"""Pydantic data models for ChatSystem Backend API.
Enforces request validation and standard JSON responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Auth Schemas ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    credential: str = Field(..., description="Email hoặc tên đăng nhập SGOD")
    password: str = Field(..., description="Mật khẩu tài khoản SGOD")
    tier: Optional[str] = Field(
        None,
        description="Tầng đăng nhập: 'enterprises', 'enterprise-users', hoặc 'sub-enterprises'. Bỏ trống để tự động nhận diện."
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token của phiên hiện tại")


class UserContext(BaseModel):
    user_id: str = Field(..., description="Định danh người dùng SGOD")
    full_name: str = Field(..., description="Họ và tên đầy đủ")
    role: str = Field(..., description="Vai trò hệ thống: 'company_admin' | 'employee' | 'system_admin'")
    tier: str = Field(..., description="Tầng đăng nhập SGOD: 'enterprises' | 'enterprise-users' | 'sub-enterprises'")
    role_vi: Optional[str] = Field(None, description="Tên vai trò hiển thị tiếng Việt")
    enterprise_name: Optional[str] = Field(None, description="Tên doanh nghiệp")


class LoginResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_context: Optional[UserContext] = None
    message: Optional[str] = None


class RefreshResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    message: Optional[str] = None


class MeResponse(BaseModel):
    success: bool
    user_context: Optional[UserContext] = None
    message: Optional[str] = None


# ── Chat Schemas ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', 'system', hoặc 'tool'")
    content: Optional[str] = Field(None, description="Nội dung tin nhắn")
    name: Optional[str] = Field(None, description="Tên công cụ (khi role là 'tool')")
    tool_call_id: Optional[str] = Field(None, description="ID của lệnh gọi công cụ")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Nội dung câu hỏi của người dùng")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Lịch sử hội thoại trước đó (nếu có)")
    refresh_token: Optional[str] = Field(None, description="Refresh token dự phòng khi thực thi công cụ SGOD")


class ToolExecutionRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ChatResponse(BaseModel):
    success: bool
    reply: str
    tools_executed: List[ToolExecutionRecord] = Field(default_factory=list)
    token_refreshed: bool = False
    new_access_token: Optional[str] = None
    message: Optional[str] = None
    response_time_ms: Optional[int] = None
    token_usage: Optional[Dict[str, int]] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    sgod_gateway: str
    gemini_configured: bool
    gemini_model: str
