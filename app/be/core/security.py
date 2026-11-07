"""Security dependencies and authentication verification for FastAPI."""

from __future__ import annotations

from typing import Optional
from fastapi import Header, HTTPException, status

from app.be.schemas import UserContext
from app.be.services import AuthService

_auth_service = AuthService()


def get_current_user_and_token(
    authorization: Optional[str] = Header(None, description="Bearer <JWT>"),
) -> tuple[UserContext, str]:
    """Dependency extracting and validating user session from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập: Thiếu Authorization header.",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Định dạng Authorization không hợp lệ. Mong đợi: 'Bearer <token>'.",
        )

    token = parts[1].strip()
    me_res = _auth_service.get_me(token)

    if not me_res.success or not me_res.user_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=me_res.message or "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        )

    return me_res.user_context, token
