"""Authentication API endpoints (/api/auth)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.be.api.deps import get_auth_service, get_current_user_and_token
from app.be.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    UserContext,
)
from app.be.services import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, summary="Đăng nhập tài khoản SGOD")
def login_endpoint(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Xác thực thông tin tài khoản qua SGOD Gateway và trả về phiên làm việc."""
    res = auth_service.login(
        credential=payload.credential,
        password=payload.password,
        tier=payload.tier,
    )
    if not res.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.message)
    return res


@router.post("/refresh", response_model=RefreshResponse, summary="Làm mới token phiên")
def refresh_endpoint(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    """Làm mới Access Token khi hết hạn bằng Refresh Token."""
    res = auth_service.refresh(payload.refresh_token)
    if not res.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.message)
    return res


@router.get("/me", response_model=MeResponse, summary="Lấy thông tin người dùng hiện tại")
def me_endpoint(
    auth_data: tuple[UserContext, str] = Depends(get_current_user_and_token),
) -> MeResponse:
    """Trả về thông tin UserContext của người dùng tương ứng với Bearer token."""
    user_ctx, _ = auth_data
    return MeResponse(success=True, user_context=user_ctx, message="OK")
