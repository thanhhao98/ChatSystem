#!/usr/bin/env python3
"""[S-V6] Unit tests for SGOD Tool Executor (tools/sgod/tool_executor.py).

Verifies all contracts:
  1. Layer 2 Authorization (policy check before network)
  2. Dynamic route mapping & parameter extraction (path params vs query params)
  3. Dual-layer headers (service x-api-key + Authorization Bearer)
  4. Multi-step resolve (Name -> ID)
  5. Envelope unwrapping & branching on body.success
  6. 401 silent token refresh and retry
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.sgod.tool_executor import SGODToolExecutor, ToolExecutionResult, execute_tool


class MockHTTPResponse:
    def __init__(self, status: int, data: bytes, headers: Optional[Dict[str, str]] = None):
        self.status = status
        self.code = status
        self._data = io.BytesIO(data)
        self.headers = headers or {"Content-Type": "application/json"}

    def read(self, amt: Optional[int] = None) -> bytes:
        return self._data.read(amt)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockOpener:
    """Mock urllib OpenerDirector to simulate SGOD Gateway responses without network."""

    def __init__(self):
        self.requests: List[urllib.request.Request] = []
        self.handlers: List[Tuple[Any, Any]] = []

    def add_handler(self, matcher, responder):
        """matcher(url, method, headers, data) -> bool, responder(...) -> (status, body_dict_or_bytes)"""
        self.handlers.append((matcher, responder))

    def open(self, req: urllib.request.Request, timeout: float = 30.0):
        self.requests.append(req)
        url = req.full_url
        method = req.get_method()
        headers = dict(req.headers)
        data = req.data

        for matcher, responder in self.handlers:
            if matcher(url, method, headers, data):
                status, body = responder(url, method, headers, data)
                if isinstance(body, dict):
                    raw = json.dumps(body).encode("utf-8")
                elif isinstance(body, str):
                    raw = body.encode("utf-8")
                else:
                    raw = body or b""

                if status >= 400:
                    fp = io.BytesIO(raw)
                    raise urllib.error.HTTPError(url, status, f"HTTP Error {status}", headers, fp)
                return MockHTTPResponse(status, raw, {"Content-Type": "application/json"})

        # Default 404 for unmocked routes
        fp = io.BytesIO(b'{"statusCode": 404, "success": false, "message": "Not found in mock"}')
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, fp)


class TestSGODToolExecutor(unittest.TestCase):

    def setUp(self):
        self.mock_opener = MockOpener()
        self.executor = SGODToolExecutor(
            base_url="http://mock-sgod:5000",
            auth_key="test-auth-key",
            asset_key="test-asset-key",
            chat_key="test-chat-key",
            opener=self.mock_opener,
        )

    def test_tc01_authz_layer2_denied(self):
        """TC-01: An employee calling get_enterprise_profile is denied immediately without network calls."""
        res = self.executor.execute(
            tool_name="get_enterprise_profile",
            arguments={},
            user_role="employee",
            access_token="valid-token",
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error, "denied")
        self.assertEqual(res.status_code, 403)
        self.assertIn("Từ chối quyền", res.message or "")
        self.assertEqual(len(self.mock_opener.requests), 0, "No network request should be sent on denied role")

    def test_tc02_authz_layer2_allowed(self):
        """TC-02: Company admin is authorized to call get_enterprise_profile."""
        self.assertTrue(self.executor.authorize("get_enterprise_profile", "company_admin"))
        self.assertFalse(self.executor.authorize("get_enterprise_profile", "employee"))
        self.assertTrue(self.executor.authorize("list_my_assets", "employee"))
        self.assertTrue(self.executor.authorize("list_my_assets", "company_admin"))

    def test_tc03_url_and_query_formatting(self):
        """TC-03: Route parameters and query string correctly constructed."""
        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-asset/v1/assets" in url,
            lambda url, m, h, d: (200, {
                "statusCode": 200,
                "success": True,
                "data": {"items": [{"id": "asset-1", "name": "Laptop"}]},
                "message": "OK",
            }),
        )

        res = self.executor.execute(
            tool_name="list_my_assets",
            arguments={"limit": 10, "search": "Laptop"},
            user_role="employee",
            access_token="user-jwt-123",
        )
        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(self.mock_opener.requests), 1)

        req = self.mock_opener.requests[0]
        self.assertIn("limit=10", req.full_url)
        self.assertIn("search=Laptop", req.full_url)
        self.assertEqual(req.headers.get("X-api-key"), "test-asset-key")
        self.assertEqual(req.headers.get("Authorization"), "Bearer user-jwt-123")
        self.assertEqual(res.data, {"items": [{"id": "asset-1", "name": "Laptop"}]})

    def test_tc04_path_param_substitution(self):
        """TC-04: Tool with {id} path parameter fills segment correctly."""
        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-asset/v1/locations/loc-999" in url,
            lambda url, m, h, d: (200, {
                "statusCode": 200,
                "success": True,
                "data": {"id": "loc-999", "name": "Kho A"},
            }),
        )

        res = self.executor.execute(
            tool_name="get_location",
            arguments={"location_id": "loc-999"},
            user_role="employee",
            access_token="jwt-abc",
        )
        self.assertTrue(res.success)
        self.assertEqual(res.data["name"], "Kho A")
        self.assertIn("/sgod-asset/v1/locations/loc-999", self.mock_opener.requests[0].full_url)

    def test_tc05_missing_path_param_returns_bad_request(self):
        """TC-05: Missing path identifier returns bad_request 400 without sending request."""
        res = self.executor.execute(
            tool_name="get_location",
            arguments={},  # missing location_id
            user_role="employee",
            access_token="jwt-abc",
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error, "bad_request")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(self.mock_opener.requests), 0)

    def test_tc06_envelope_unwrap_error_on_http_200(self):
        """TC-06: Envelope with HTTP 200 but body.success: false is correctly classified as error."""
        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-asset/v1/locations/nonexistent" in url,
            lambda url, m, h, d: (200, {
                "statusCode": 404,
                "success": False,
                "data": None,
                "message": "Địa điểm không tồn tại",
            }),
        )

        res = self.executor.execute(
            tool_name="get_location",
            arguments={"location_id": "nonexistent"},
            user_role="employee",
            access_token="jwt-abc",
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error, "not_found")
        self.assertEqual(res.status_code, 404)
        self.assertIn("Địa điểm không tồn tại", res.message or "")

    def test_tc07_resolve_asset_ref_with_24hex_oid_bypasses_resolve(self):
        """TC-07: An asset_ref that is a 24-character hex ObjectId bypasses search resolve."""
        oid = "653b4fa12ef90123456789ab"
        self.mock_opener.add_handler(
            lambda url, m, h, d: f"/sgod-asset/v1/assets/{oid}" in url and "search=" not in url,
            lambda url, m, h, d: (200, {
                "statusCode": 200,
                "success": True,
                "data": {"id": oid, "name": "Máy tính Dell"},
            }),
        )

        res = self.executor.execute(
            tool_name="get_asset",
            arguments={"asset_ref": oid},
            user_role="employee",
            access_token="jwt-abc",
        )
        self.assertTrue(res.success)
        self.assertEqual(len(self.mock_opener.requests), 1, "Should directly call detail without search")
        self.assertIn(f"/sgod-asset/v1/assets/{oid}", self.mock_opener.requests[0].full_url)

    def test_tc08_resolve_asset_ref_with_name_performs_search_then_detail(self):
        """TC-08: An asset_ref by name runs search first to find ObjectId, then calls detail route."""
        resolved_oid = "653b4fa12ef90123456789ab"

        # 1. Search resolve route
        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-asset/v1/assets?search=Macbook" in url,
            lambda url, m, h, d: (200, {
                "statusCode": 200,
                "success": True,
                "data": {"items": [{"id": resolved_oid, "name": "Macbook Pro 16", "assetCode": "TS001"}]},
            }),
        )
        # 2. Detail route
        self.mock_opener.add_handler(
            lambda url, m, h, d: f"/sgod-asset/v1/assets/{resolved_oid}" in url and "search=" not in url,
            lambda url, m, h, d: (200, {
                "statusCode": 200,
                "success": True,
                "data": {"id": resolved_oid, "name": "Macbook Pro 16", "status": "ACTIVE"},
            }),
        )

        res = self.executor.execute(
            tool_name="get_asset",
            arguments={"asset_ref": "Macbook"},
            user_role="employee",
            access_token="jwt-abc",
        )
        self.assertTrue(res.success)
        self.assertEqual(res.data["name"], "Macbook Pro 16")
        self.assertEqual(len(self.mock_opener.requests), 2, "Search call followed by detail call")

    def test_tc09_silent_token_refresh_on_401(self):
        """TC-09: Encountering 401 triggers silent refresh with refreshToken and retries tool call."""
        call_count = {"count": 0}

        def asset_handler(url, m, h, d):
            call_count["count"] += 1
            auth_header = h.get("Authorization") or h.get("authorization") or ""
            if "new-access-token" in auth_header:
                return 200, {
                    "statusCode": 200,
                    "success": True,
                    "data": {"items": [{"id": "item-1"}]},
                }
            # First attempt: token expired
            return 401, {
                "statusCode": 401,
                "success": False,
                "message": "Token expired",
            }

        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-asset/v1/assets" in url,
            asset_handler,
        )

        # Refresh route
        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-auth/v1/sessions/refresh" in url and m == "POST",
            lambda url, m, h, d: (200, {
                "statusCode": 200,
                "success": True,
                "data": {
                    "accessToken": "new-access-token",
                    "refreshToken": "new-refresh-token",
                },
            }),
        )

        res = self.executor.execute(
            tool_name="list_my_assets",
            arguments={"limit": 5},
            user_role="employee",
            access_token="expired-token",
            refresh_token="valid-refresh-token",
        )

        self.assertTrue(res.success)
        self.assertTrue(res.token_refreshed)
        self.assertEqual(res.new_access_token, "new-access-token")
        self.assertEqual(res.new_refresh_token, "new-refresh-token")
        self.assertEqual(len(self.mock_opener.requests), 3, "1. Failed call -> 2. Refresh call -> 3. Retried call")

    def test_tc10_unauthorized_when_refresh_fails(self):
        """TC-10: When 401 happens and refresh also fails, returns unauthorized error."""
        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-asset/v1/assets" in url,
            lambda url, m, h, d: (401, {
                "statusCode": 401,
                "success": False,
                "message": "Token expired",
            }),
        )
        self.mock_opener.add_handler(
            lambda url, m, h, d: "/sgod-auth/v1/sessions/refresh" in url,
            lambda url, m, h, d: (401, {
                "statusCode": 401,
                "success": False,
                "message": "Refresh token expired",
            }),
        )

        res = self.executor.execute(
            tool_name="list_my_assets",
            arguments={},
            user_role="employee",
            access_token="expired-token",
            refresh_token="invalid-refresh",
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error, "unauthorized")
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.token_refreshed)

    def test_tc11_nonexistent_tool_returns_not_found(self):
        """TC-11: An unknown tool name returns not_found 404."""
        res = self.executor.execute(
            tool_name="unknown_tool_xyz",
            arguments={},
            user_role="employee",
            access_token="tok",
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error, "not_found")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
