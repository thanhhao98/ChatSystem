#!/usr/bin/env python3
"""[S-V7] Unit tests for ChatSystem Backend (app/be/).

Verifies:
  1. Contract 3 compliance in build_user_context() (roles, names, tiers)
  2. Preamble rendering with slots
  3. Role-based tool filtering (employee vs company_admin)
  4. Auth Proxy endpoints (/api/auth/login, /api/auth/refresh, /api/auth/me)
  5. Chat Engine Agentic tool-calling loop and fallback
  6. Health check endpoint (/api/health)
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.be import schemas
from app.be.main import app
from app.be.services import (
    build_user_context,
    filter_tools_for_role,
    render_preamble,
)


class TestBackendAuthAndChat(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_tc01_build_user_context_contract3(self):
        """TC-01: Verifies build_user_context strictly respects Contract 3."""
        # Enterprise tier -> company_admin
        user_raw = {
            "id": "user-123",
            "fullName": {"firstName": "Thuong", "lastName": "Admin"},
            "userType": "enterprise",
            "enterpriseName": "Acme Corp",
        }
        ctx = build_user_context(user_raw, tier="enterprises")
        self.assertEqual(ctx.user_id, "user-123")
        self.assertEqual(ctx.full_name, "Thuong Admin")
        self.assertEqual(ctx.role, "company_admin")
        self.assertEqual(ctx.tier, "enterprises")
        self.assertEqual(ctx.role_vi, "Quản trị viên doanh nghiệp")
        self.assertEqual(ctx.enterprise_name, "Acme Corp")

        # Enterprise-users tier -> employee
        emp_raw = {
            "id": "emp-456",
            "fullName": "Nguyen Van A",
            "userType": "enterprise_user",
        }
        ctx_emp = build_user_context(emp_raw, tier="enterprise-users")
        self.assertEqual(ctx_emp.role, "employee")
        self.assertEqual(ctx_emp.role_vi, "Nhân viên")
        self.assertEqual(ctx_emp.full_name, "Nguyen Van A")

    def test_tc02_filter_tools_for_role(self):
        """TC-02: Role-based filtering ensures employee cannot call admin-only tools."""
        emp_tools = filter_tools_for_role("employee")
        admin_tools = filter_tools_for_role("company_admin")

        emp_names = {t["function"]["name"] for t in emp_tools}
        admin_names = {t["function"]["name"] for t in admin_tools}

        self.assertIn("list_my_assets", emp_names)
        self.assertIn("list_my_assets", admin_names)

        # Admin-only tools must NOT be in employee tools
        self.assertNotIn("get_enterprise_profile", emp_names)
        self.assertIn("get_enterprise_profile", admin_names)
        self.assertNotIn("list_enterprise_users", emp_names)
        self.assertIn("list_enterprise_users", admin_names)

    def test_tc03_render_preamble_slots(self):
        """TC-03: Render preamble replaces slots without disturbing JSON syntax."""
        ctx = schemas.UserContext(
            user_id="usr-999",
            full_name="Le Van Test",
            role="employee",
            tier="enterprise-users",
            role_vi="Nhân viên",
        )
        rendered = render_preamble(ctx)
        self.assertIn("Le Van Test", rendered)
        self.assertIn("Nhân viên", rendered)
        self.assertNotIn("{full_name}", rendered)
        self.assertNotIn("{role_vi}", rendered)

    def test_tc04_health_endpoint(self):
        """TC-04: GET /api/health returns 200 OK and status."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("sgod_gateway", data)

    @patch("app.be.services.auth_service.send_sgod_request")
    def test_tc05_login_endpoint_success(self, mock_send):
        """TC-05: POST /api/auth/login proxies successfully to SGOD and returns tokens."""
        mock_send.return_value = (
            200,
            {
                "success": True,
                "data": {
                    "accessToken": "mock-access-token-xyz",
                    "refreshToken": "mock-refresh-token-abc",
                    "user": {
                        "id": "6a6393308f5053311da6caa5",
                        "fullName": {"firstName": "Thuong", "lastName": "Admin"},
                        "userType": "enterprise",
                        "enterpriseName": "Test Inc",
                    },
                },
            },
            None,
        )

        resp = self.client.post(
            "/api/auth/login",
            json={"credential": "test@example.com", "password": "pass", "tier": "enterprises"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["access_token"], "mock-access-token-xyz")
        self.assertEqual(data["user_context"]["role"], "company_admin")

    @patch("app.be.services.auth_service.send_sgod_request")
    def test_tc06_login_endpoint_failure(self, mock_send):
        """TC-06: POST /api/auth/login returns 401 on bad credentials."""
        mock_send.return_value = (
            401,
            {"success": False, "statusCode": 401, "message": "Invalid credentials"},
            None,
        )

        resp = self.client.post(
            "/api/auth/login",
            json={"credential": "bad@example.com", "password": "wrong"},
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid credentials", resp.json()["detail"])

    @patch("tools.sgod.tool_executor.SGODToolExecutor.execute")
<<<<<<< HEAD
    @patch("app.be.gemini_client.GeminiClient.chat_completion")
    @patch("app.be.routes.get_me_proxy")
    def test_tc07_chat_endpoint_with_tool_loop(self, mock_get_me, mock_chat, mock_executor):
        """TC-07: POST /api/chat executes tool-calling loop and returns response."""
=======
    @patch("app.be.clients.gemini_client.GeminiClient.chat_completion_stream")
    @patch("app.be.services.auth_service.AuthService.get_me")
    def test_tc07_chat_stream_endpoint_with_tool_loop(self, mock_get_me, mock_chat_stream, mock_executor):
        """TC-07: POST /api/chat/stream executes tool-calling streaming loop and returns SSE events."""
>>>>>>> 499781f2e8f16911e949268264bfd77f9a98fd4f
        from tools.sgod.tool_executor import ToolExecutionResult

        mock_get_me.return_value = schemas.MeResponse(
            success=True,
            user_context=schemas.UserContext(
                user_id="usr-1",
                full_name="Tester",
                role="company_admin",
                tier="enterprises",
                role_vi="Quản trị viên doanh nghiệp",
            ),
        )

<<<<<<< HEAD
        # Mock Gemini first returning a tool_call, then returning final answer
        mock_chat.side_effect = [
            (
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
=======
        # Mock Gemini stream: 1st turn emits tool call, 2nd turn emits delta and usage
        mock_chat_stream.side_effect = [
            iter([
                (
                    "tool_calls",
                    [
>>>>>>> 499781f2e8f16911e949268264bfd77f9a98fd4f
                        {
                            "id": "call_mock_1",
                            "type": "function",
                            "function": {
                                "name": "list_my_assets",
                                "arguments": json.dumps({"limit": 5}),
                            },
                        }
                    ],
<<<<<<< HEAD
                },
                None,
            ),
            (
                {
                    "role": "assistant",
                    "content": "Dưới đây là danh sách tài sản của bạn từ hệ thống SGOD.",
                },
                None,
            ),
=======
                )
            ]),
            iter([
                ("delta", "Dưới đây là danh sách tài sản của bạn từ hệ thống SGOD."),
                ("usage", {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}),
            ]),
>>>>>>> 499781f2e8f16911e949268264bfd77f9a98fd4f
        ]

        # Mock executor returning success
        mock_executor.return_value = ToolExecutionResult(
            success=True,
            status_code=200,
            data={"items": [{"id": "ast-1", "name": "Màn hình Dell"}]},
        )

        resp = self.client.post(
            "/api/chat/stream",
            headers={"Authorization": "Bearer fake-token-123"},
            json={"message": "Cho tôi xem danh sách tài sản của tôi"},
        )
        self.assertEqual(resp.status_code, 200)
<<<<<<< HEAD
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["tools_executed"]), 1)
        self.assertEqual(data["tools_executed"][0]["tool_name"], "list_my_assets")
        self.assertIn("danh sách tài sản", data["reply"])
=======
        self.assertIn("text/event-stream", resp.headers["content-type"])
        body_text = resp.text
        self.assertIn("tool_start", body_text)
        self.assertIn("list_my_assets", body_text)
        self.assertIn("tool_result", body_text)
        self.assertIn("done", body_text)
        self.assertIn("danh sách tài sản", body_text)
>>>>>>> 499781f2e8f16911e949268264bfd77f9a98fd4f


if __name__ == "__main__":
    unittest.main()
