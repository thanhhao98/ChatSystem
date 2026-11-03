#!/usr/bin/env python3
"""[S-V6] SGOD Tool Executor — adapter executing function-calling tool calls against live SGOD API Gateway.

Contract & Behavior (docs/architecture.md, docs/roadmap.md, docs/sgod-api-reference.md):
  1. Layer 2 Authorization:
     Verifies user_role in tool_policy.json[tool_name]['roles']. If unauthorized, rejects immediately
     with status_code=403 and error='denied' WITHOUT sending any network request.
  2. Route & Metadata:
     Loads tool definitions from tools/sgod/sgod_tools.json (22 read-only tools). Reads x_sgod:
     service ('asset', 'auth', 'chat'), method ('GET'), path template ('/sgod-asset/v1/assets/{id}'),
     id_params, and resolve query.
  3. Two Credentials (Dual-layer Header):
     - x-api-key: SGOD_<SERVICE>_API_KEY from environment
     - Authorization: Bearer <access_token> (user JWT for identity scoping)
  4. Multi-step Resolve (Name -> ID):
     If tool has x_sgod.resolve (e.g., get_asset, get_asset_histories) and asset_ref is NOT a 24-hex ObjectId,
     runs resolve GET /sgod-asset/v1/assets?search=<asset_ref> to retrieve the real MongoDB ObjectId before calling
     the detail route.
  5. Envelope Unwrapping & Status Classification:
     Branches strictly on body['success'] (True / False), NEVER on HTTP status code alone (since SGOD Gateway
     can return HTTP 200 with success: false). Unwraps body['data'].
  6. Silent Session Renewal on 401:
     When encountering HTTP 401 or body.statusCode == 401: if refresh_token is provided, calls
     POST /sgod-auth/v1/sessions/refresh to renew access_token and retries the tool call once.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

OID_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")
RESOLVE_RE = re.compile(r"^(GET) (/sgod-[a-z]+/v1/[^?\s{}]+)\?([A-Za-z_][A-Za-z0-9_]*)=\{([a-z][a-z0-9_]*)\}$")
REFRESH_PATH = "/sgod-auth/v1/sessions/refresh"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOOLS_PATH = REPO_ROOT / "tools" / "sgod" / "sgod_tools.json"
DEFAULT_POLICY_PATH = REPO_ROOT / "tools" / "sgod" / "tool_policy.json"


@dataclass
class ToolExecutionResult:
    """Standard execution result returned to caller / chat engine."""
    success: bool
    data: Any = None
    error: Optional[str] = None          # 'denied' | 'not_found' | 'unauthorized' | 'bad_request' | 'network_error' | 'server_error'
    message: Optional[str] = None        # Human-readable message
    status_code: int = 200
    token_refreshed: bool = False        # True if silent token refresh succeeded
    new_access_token: Optional[str] = None
    new_refresh_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        d = {
            "success": self.success,
            "status_code": self.status_code,
        }
        if self.data is not None:
            d["data"] = self.data
        if self.error:
            d["error"] = self.error
        if self.message:
            d["message"] = self.message
        if self.token_refreshed:
            d["token_refreshed"] = True
            d["new_access_token"] = self.new_access_token
            if self.new_refresh_token:
                d["new_refresh_token"] = self.new_refresh_token
        return d


class SGODToolExecutor:
    """SGOD Adapter executing tool calls against SGOD Gateway."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        tools_path: Optional[Union[str, Path]] = None,
        policy_path: Optional[Union[str, Path]] = None,
        auth_key: Optional[str] = None,
        asset_key: Optional[str] = None,
        chat_key: Optional[str] = None,
        timeout: float = 30.0,
        opener: Optional[urllib.request.OpenerDirector] = None,
    ) -> None:
        raw_base = base_url or os.environ.get("SGOD_BASE_URL", "")
        self.base_url = raw_base.strip().rstrip("/")
        self.timeout = timeout
        self._opener = opener or urllib.request.build_opener()

        # Service API Keys (read from params or environment)
        self.keys = {
            "auth": (auth_key or os.environ.get("SGOD_AUTH_API_KEY", "")).strip(),
            "asset": (asset_key or os.environ.get("SGOD_ASSET_API_KEY", "")).strip(),
            "chat": (chat_key or os.environ.get("SGOD_CHAT_API_KEY", "")).strip(),
        }

        # Load tools and policy
        self.tools_path = Path(tools_path) if tools_path else DEFAULT_TOOLS_PATH
        self.policy_path = Path(policy_path) if policy_path else DEFAULT_POLICY_PATH

        self.tools: Dict[str, Dict[str, Any]] = self._load_tools(self.tools_path)
        self.policy: Dict[str, Dict[str, Any]] = self._load_policy(self.policy_path)

    @staticmethod
    def _load_tools(path: Path) -> Dict[str, Dict[str, Any]]:
        if not path.is_file():
            return {}
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {item["function"]["name"]: item for item in data if "function" in item}

    @staticmethod
    def _load_policy(path: Path) -> Dict[str, Dict[str, Any]]:
        if not path.is_file():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def authorize(self, tool_name: str, user_role: str) -> bool:
        """Layer 2 Authorization check against tool_policy.json.
        Allowed iff user_role in policy[tool_name]['roles'].
        Unknown tool or empty policy returns False.
        """
        entry = self.policy.get(tool_name)
        if not isinstance(entry, dict):
            return False
        allowed_roles = entry.get("roles") or []
        return user_role in allowed_roles

    def _key_for(self, service: str) -> str:
        return self.keys.get(service, "")

    def _send_http(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
        """Perform HTTP request to SGOD Gateway.
        Returns: (http_status, parsed_json_body, error_text)
        """
        url = self.base_url + path
        if query:
            clean_query = {k: v for k, v in query.items() if v is not None}
            if clean_query:
                url += "?" + urllib.parse.urlencode(clean_query)

        service = "asset"
        if "/sgod-auth/" in path:
            service = "auth"
        elif "/sgod-chat/" in path:
            service = "chat"

        headers = {
            "Accept": "application/json",
            "x-api-key": self._key_for(service),
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
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
        except (UnicodeDecodeError, json.JSONDecodeError):
            return status, None, f"non_json_body: {len(raw)} bytes"

    def _refresh_session(
        self,
        refresh_token: str,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Call POST /sgod-auth/v1/sessions/refresh.
        Returns: (success, new_access_token, new_refresh_token, error_message)
        """
        status, body, err = self._send_http(
            method="POST",
            path=REFRESH_PATH,
            body={"refreshToken": refresh_token},
        )
        if err or not isinstance(body, dict):
            return False, None, None, err or f"HTTP {status}"

        if not body.get("success"):
            return False, None, None, body.get("message") or f"HTTP {status}"

        data = body.get("data")
        if not isinstance(data, dict) or not data.get("accessToken"):
            return False, None, None, "missing accessToken in refresh response"

        new_access = data["accessToken"]
        new_refresh = data.get("refreshToken") or refresh_token
        return True, new_access, new_refresh, None

    def _resolve_asset_ref(
        self,
        ref_value: str,
        token: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Multi-step resolve: resolve asset name / code to MongoDB ObjectId.
        If ref_value is already a 24-hex ObjectId, returns (ref_value, None) immediately.
        Otherwise calls GET /sgod-asset/v1/assets?search=<ref_value>.
        Returns: (resolved_id, error_message)
        """
        if not ref_value or not isinstance(ref_value, str):
            return None, "empty asset reference"

        # Contract: 24 hex string is already an ObjectId -> bypass resolve
        if OID_PATTERN.match(ref_value.strip()):
            return ref_value.strip(), None

        # Call search route
        resolve_path = "/sgod-asset/v1/assets"
        status, body, err = self._send_http(
            method="GET",
            path=resolve_path,
            query={"search": ref_value.strip(), "limit": 5},
            token=token,
        )

        if err:
            return None, f"Resolve failed: {err}"
        if not isinstance(body, dict) or not body.get("success"):
            msg = body.get("message") if isinstance(body, dict) else f"HTTP {status}"
            return None, f"Resolve failed: {msg}"

        data = body.get("data")
        items = []
        if isinstance(data, dict):
            items = data.get("items") or []
        elif isinstance(data, list):
            items = data

        if not items:
            return None, f"Không tìm thấy tài sản nào khớp với '{ref_value}'"

        # Find best match or take first item
        match = None
        query_lower = ref_value.strip().lower()
        for item in items:
            if not isinstance(item, dict):
                continue
            code = str(item.get("assetCode") or "").lower()
            name = str(item.get("name") or "").lower()
            if query_lower in (code, name):
                match = item
                break

        if match is None:
            match = items[0]

        target_id = match.get("id") or match.get("_id")
        if not target_id:
            return None, f"Tài sản khớp với '{ref_value}' nhưng thiếu trường id"

        return str(target_id), None

    def execute(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        user_role: str = "employee",
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> ToolExecutionResult:
        """Execute a tool call with authz, resolution, dual headers, envelope unwrapping, and 401 retry."""
        args = dict(arguments or {})

        # 1. Tool existence check
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolExecutionResult(
                success=False,
                error="not_found",
                message=f"Công cụ '{tool_name}' không tồn tại trong danh mục SGOD.",
                status_code=404,
            )

        # 2. Layer 2 Authorization check (policy gate)
        if not self.authorize(tool_name, user_role):
            return ToolExecutionResult(
                success=False,
                error="denied",
                message=f"Từ chối quyền: Vai trò '{user_role}' không được phép gọi công cụ '{tool_name}'.",
                status_code=403,
            )

        x_sgod = tool.get("x_sgod", {})
        if x_sgod.get("method") != "GET" or x_sgod.get("writes") is not False:
            return ToolExecutionResult(
                success=False,
                error="bad_request",
                message=f"Công cụ '{tool_name}' không phải là GET chỉ-đọc (writes: false).",
                status_code=400,
            )

        # 3. Resolve asset_ref if required
        id_params = x_sgod.get("id_params") or []
        has_resolve = bool(x_sgod.get("resolve"))

        token_refreshed = False
        new_access = None
        new_refresh = None
        cur_token = access_token

        if has_resolve and "asset_ref" in id_params:
            ref_val = args.get("asset_ref")
            if ref_val is not None:
                resolved_id, r_err = self._resolve_asset_ref(str(ref_val), cur_token)
                if r_err:
                    return ToolExecutionResult(
                        success=False,
                        error="not_found",
                        message=r_err,
                        status_code=404,
                    )
                args["asset_ref"] = resolved_id

        # 4. Build path template and query parameters
        path_template = x_sgod.get("path", "")
        real_path = path_template
        query_params: Dict[str, Any] = {}

        # Fill {id} in path segment from id_params or 'id'
        if "{id}" in path_template:
            val = None
            for p in id_params:
                if p in args:
                    val = args.pop(p)
                    break
            if val is None and "id" in args:
                val = args.pop("id")
            if val is None:
                return ToolExecutionResult(
                    success=False,
                    error="bad_request",
                    message=f"Thiếu tham số định danh cho đường dẫn '{path_template}'.",
                    status_code=400,
                )
            real_path = path_template.replace("{id}", urllib.parse.quote(str(val), safe=""))

        # Remaining arguments become query parameters
        for k, v in args.items():
            if v is not None:
                query_params[k] = v

        # 5. Call SGOD Gateway
        status, body, err = self._send_http(
            method="GET",
            path=real_path,
            query=query_params,
            token=cur_token,
        )

        # 6. Check for 401 Unauthorized -> silent refresh and retry
        is_unauthorized = (status == 401) or (
            isinstance(body, dict)
            and body.get("success") is False
            and body.get("statusCode") == 401
        )

        if is_unauthorized and refresh_token:
            r_ok, r_acc, r_ref, r_msg = self._refresh_session(refresh_token)
            if r_ok and r_acc:
                token_refreshed = True
                new_access = r_acc
                new_refresh = r_ref
                cur_token = r_acc

                # Retry request with new token
                status, body, err = self._send_http(
                    method="GET",
                    path=real_path,
                    query=query_params,
                    token=cur_token,
                )
            else:
                return ToolExecutionResult(
                    success=False,
                    error="unauthorized",
                    message=f"Phiên đăng nhập hết hạn và làm mới thất bại: {r_msg}",
                    status_code=401,
                )

        if is_unauthorized and not token_refreshed:
            return ToolExecutionResult(
                success=False,
                error="unauthorized",
                message="Phiên làm việc hết hạn hoặc không hợp lệ (401 Unauthorized).",
                status_code=401,
            )

        if err:
            return ToolExecutionResult(
                success=False,
                error="network_error",
                message=f"Lỗi kết nối tới SGOD Gateway: {err}",
                status_code=status or 502,
                token_refreshed=token_refreshed,
                new_access_token=new_access,
                new_refresh_token=new_refresh,
            )

        # 7. Envelope unwrapping (strictly on body.success)
        if not isinstance(body, dict):
            return ToolExecutionResult(
                success=False,
                error="server_error",
                message="Phản hồi từ SGOD Gateway không phải là JSON hợp lệ.",
                status_code=status,
                token_refreshed=token_refreshed,
                new_access_token=new_access,
                new_refresh_token=new_refresh,
            )

        is_success = body.get("success") is True
        sc = body.get("statusCode") or status
        data = body.get("data")
        msg = body.get("message")

        if is_success:
            return ToolExecutionResult(
                success=True,
                data=data,
                message=msg or "Success",
                status_code=sc,
                token_refreshed=token_refreshed,
                new_access_token=new_access,
                new_refresh_token=new_refresh,
            )

        # Handle body.success == False
        err_type = "error"
        if sc == 404:
            err_type = "not_found"
        elif sc == 403:
            err_type = "forbidden"
        elif sc == 400:
            err_type = "bad_request"
        elif sc and sc >= 500:
            err_type = "server_error"

        return ToolExecutionResult(
            success=False,
            data=data,
            error=err_type,
            message=msg or f"SGOD API trả về lỗi {sc}",
            status_code=sc,
            token_refreshed=token_refreshed,
            new_access_token=new_access,
            new_refresh_token=new_refresh,
        )


def execute_tool(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    user_role: str = "employee",
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    executor: Optional[SGODToolExecutor] = None,
) -> ToolExecutionResult:
    """Convenience top-level function for chat engine."""
    exe = executor or SGODToolExecutor()
    return exe.execute(
        tool_name=tool_name,
        arguments=arguments,
        user_role=user_role,
        access_token=access_token,
        refresh_token=refresh_token,
    )
