"""Authentication Service & Proxy module for ChatSystem Backend.
Handles SGOD session authentication, token refresh, and user context construction per Contract 3.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from app.be import config
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

    # Determine role from tier
    role = tier_map.get(tier, "employee")

    # Format full_name
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


def _send_sgod_request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    timeout: float = 15.0,
) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
    """Helper to dispatch requests to SGOD Gateway with static auth x-api-key."""
    url = config.SGOD_BASE_URL + path
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": config.SGOD_AUTH_API_KEY,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data_bytes = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
    except Exception as e:
        return 0, None, f"network_error: {type(e).__name__}"

    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else {}
        return status, parsed, None
    except Exception:
        return status, None, "non_json_body"


def login_proxy(credential: str, password: str, tier: Optional[str] = None) -> LoginResponse:
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

        # Send standard SGOD LoginRequestDto payload ({credential, password})
        payload = {"credential": credential.strip(), "password": password}
        status, res_json, err = _send_sgod_request("POST", path, body=payload)
        if err:
            last_error = f"Lỗi kết nối tới SGOD Gateway: {err}"
            continue

        if isinstance(res_json, dict) and res_json.get("success") is True:
            data = res_json.get("data") or {}
            access_token = data.get("accessToken")
            refresh_token = data.get("refreshToken")
            user_data = data.get("user") if isinstance(data.get("user"), dict) else {}

            # Prefer data.user if present; otherwise fetch profile from /users/myself
            if not user_data and access_token:
                _, me_json, me_err = _send_sgod_request(
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


def refresh_proxy(refresh_token: str) -> RefreshResponse:
    """Call POST /sgod-auth/v1/sessions/refresh to renew access token."""
    path = "/sgod-auth/v1/sessions/refresh"
    status, res_json, err = _send_sgod_request("POST", path, body={"refreshToken": refresh_token})

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


def get_me_proxy(access_token: str) -> MeResponse:
    """Verify session and retrieve current user context from GET /sgod-auth/v1/users/myself."""
    path = "/sgod-auth/v1/users/myself"
    status, res_json, err = _send_sgod_request("GET", path, token=access_token)

    if err:
        return MeResponse(success=False, message=f"Lỗi kết nối: {err}")

    if isinstance(res_json, dict) and res_json.get("success") is True:
        user_data = res_json.get("data") or {}
        user_type = str(user_data.get("userType") or "").lower()

        # Deducing tier from userType
        tier = "enterprises" if user_type == "enterprise" else "enterprise-users"
        user_ctx = build_user_context(user_data, tier)
        return MeResponse(success=True, user_context=user_ctx, message="OK")

    msg = res_json.get("message") if isinstance(res_json, dict) else f"HTTP {status}"
    return MeResponse(success=False, message=msg or "Phiên không hợp lệ hoặc đã hết hạn")
