"""Authentication and user context service conforming to Contract 3."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.be.clients import send_sgod_request
from app.be.core import config
from app.be.schemas import LoginResponse, MeResponse, RefreshResponse, UserContext

TIER_ORDER: List[str] = ["enterprises", "enterprise-users", "sub-enterprises"]


def load_roles_doc() -> Dict[str, Any]:
    """Load roles mapping document from tools/sgod/roles.json."""
    if config.ROLES_PATH.is_file():
        try:
            with config.ROLES_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "roles": ["employee", "company_admin", "system_admin"],
        "tiers": {
            "enterprises": "company_admin",
            "enterprise-users": "employee",
            "sub-enterprises": "employee",
        },
        "role_names_vi": {
            "employee": "Nhân viên",
            "company_admin": "Quản trị viên doanh nghiệp",
            "system_admin": "Quản trị hệ thống",
        },
    }


def build_user_context(user_data: Dict[str, Any], tier: str) -> UserContext:
    """Build canonical UserContext strictly conforming to Contract 3 (docs/contracts/roles.md §4).
    Priority: Tier = endpoint đăng nhập thành công -> roles.json['tiers'][tier].
    Extracts user_id, full_name, and role_vi without carrying any sensitive passwords or tenant IDs.
    """
    roles_doc = load_roles_doc()
    tier_map = roles_doc.get("tiers", {})
    names_vi = roles_doc.get("role_names_vi", {})

    role = tier_map.get(tier, "employee")

    fn_field = user_data.get("fullName")
    full_name = ""
    if isinstance(fn_field, dict):
        first = str(fn_field.get("firstName") or "").strip()
        last = str(fn_field.get("lastName") or "").strip()
        full_name = f"{first} {last}".strip()
    elif isinstance(fn_field, str):
        full_name = fn_field.strip()

    if not full_name:
        full_name = str(user_data.get("userName") or user_data.get("email") or "Người dùng").strip()

    user_id = str(user_data.get("id") or user_data.get("_id") or "usr-001")
    enterprise_name = user_data.get("enterpriseName")
    role_vi = names_vi.get(role, "Nhân viên")

    return UserContext(
        user_id=user_id,
        full_name=full_name,
        role=role,
        tier=tier,
        role_vi=role_vi,
        enterprise_name=enterprise_name,
    )


class AuthService:
    """Service handling authentication flows and session proxies."""

    def __init__(self, request_fn: Optional[Callable[..., Tuple[int, Optional[Dict[str, Any]], Optional[str]]]] = None) -> None:
        self._request_fn = request_fn

    def _dispatch_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        timeout: float = 15.0,
    ) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
        if self._request_fn is not None:
            return self._request_fn(method=method, path=path, body=body, token=token, timeout=timeout)
        return send_sgod_request(method=method, path=path, body=body, token=token, timeout=timeout)

    def login(self, credential: str, password: str, tier: Optional[str] = None) -> LoginResponse:
        """Authenticate with SGOD Gateway.
        If tier is provided, calls that tier's session route.
        If tier is None, probes tiers in priority order ('enterprises' -> 'enterprise-users' -> 'sub-enterprises').
        """
        tiers_to_try = [tier] if tier else TIER_ORDER
        last_error = "Đăng nhập thất bại"

        for current_tier in tiers_to_try:
            if not current_tier:
                continue
            path = f"/sgod-auth/v1/{current_tier}/sessions"
            payload = {"credential": credential.strip(), "password": password}

            status, res_json, err = self._dispatch_request("POST", path, body=payload)
            if err:
                last_error = f"Lỗi kết nối tới SGOD Gateway: {err}"
                continue

            if isinstance(res_json, dict) and res_json.get("success") is True:
                data = res_json.get("data") or {}
                access_token = data.get("accessToken")
                refresh_token = data.get("refreshToken")
                user_data = data.get("user") if isinstance(data.get("user"), dict) else {}

                if not user_data and access_token:
                    _, me_json, me_err = self._dispatch_request(
                        "GET", "/sgod-auth/v1/users/myself", token=access_token
                    )
                    if not me_err and isinstance(me_json, dict) and me_json.get("success") is True:
                        me_data = me_json.get("data")
                        if isinstance(me_data, dict):
                            user_data = me_data

                user_ctx = build_user_context(user_data, current_tier)
                return LoginResponse(
                    success=True,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user_context=user_ctx,
                    message="Đăng nhập thành công",
                )

            if isinstance(res_json, dict):
                msg = res_json.get("message")
                if msg:
                    last_error = msg if isinstance(msg, str) else "; ".join(str(x) for x in msg)

        return LoginResponse(success=False, message=last_error)

    def refresh(self, refresh_token: str) -> RefreshResponse:
        """Call POST /sgod-auth/v1/sessions/refresh to renew access token."""
        path = "/sgod-auth/v1/sessions/refresh"
        status, res_json, err = self._dispatch_request("POST", path, body={"refreshToken": refresh_token})

        if err:
            return RefreshResponse(success=False, message=f"Lỗi kết nối: {err}")

        if isinstance(res_json, dict) and res_json.get("success") is True:
            data = res_json.get("data") or {}
            new_access = data.get("accessToken")
            new_refresh = data.get("refreshToken") or refresh_token
            return RefreshResponse(
                success=True,
                access_token=new_access,
                refresh_token=new_refresh,
                message="Làm mới token thành công",
            )

        msg = res_json.get("message") if isinstance(res_json, dict) else f"HTTP {status}"
        return RefreshResponse(success=False, message=msg or "Làm mới phiên thất bại")

    def get_me(self, access_token: str) -> MeResponse:
        """Verify session and retrieve current user context from GET /sgod-auth/v1/users/myself."""
        path = "/sgod-auth/v1/users/myself"
        status, res_json, err = self._dispatch_request("GET", path, token=access_token)

        if err:
            return MeResponse(success=False, message=f"Lỗi kết nối: {err}")

        if isinstance(res_json, dict) and res_json.get("success") is True:
            user_data = res_json.get("data") or {}
            user_type = str(user_data.get("userType") or "").lower()
            tier = "enterprises" if user_type == "enterprise" else "enterprise-users"
            user_ctx = build_user_context(user_data, tier)
            return MeResponse(success=True, user_context=user_ctx, message="OK")

        msg = res_json.get("message") if isinstance(res_json, dict) else f"HTTP {status}"
        return MeResponse(success=False, message=msg or "Phiên không hợp lệ hoặc đã hết hạn")
