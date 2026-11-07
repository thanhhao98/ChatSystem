"""Authentication and user context schemas."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    credential: str = Field(..., description="Email hoặc tên đăng nhập SGOD")
    password: str = Field(..., description="Mật khẩu tài khoản SGOD")
    tier: Optional[str] = Field(
        None,
        description="Tầng đăng nhập: 'enterprises', 'enterprise-users', hoặc 'sub-enterprises'. Bỏ trống để tự động nhận diện.",
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
