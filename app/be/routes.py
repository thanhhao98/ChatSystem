"""FastAPI route handlers for Authentication, Chat, and Tools discovery.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.be.auth import get_me_proxy, login_proxy, refresh_proxy
from app.be.chat_engine import ChatEngine, filter_tools_for_role
from app.be.schemas import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    UserContext,
)

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])
chat_router = APIRouter(prefix="/api/chat", tags=["Chat"])
tools_router = APIRouter(prefix="/api/tools", tags=["Tools"])

_chat_engine = ChatEngine()


def get_current_user_and_token(
    authorization: Optional[str] = Header(None, description="Bearer <JWT>")
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
    me_res = get_me_proxy(token)
    if not me_res.success or not me_res.user_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=me_res.message or "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        )

    return me_res.user_context, token


# ── Auth Endpoints ───────────────────────────────────────────────────────────

@auth_router.post("/login", response_model=LoginResponse, summary="Đăng nhập tài khoản SGOD")
def login_endpoint(payload: LoginRequest):
    """Xác thực thông tin tài khoản qua SGOD Gateway và trả về phiên làm việc."""
    res = login_proxy(
        credential=payload.credential,
        password=payload.password,
        tier=payload.tier,
    )
    if not res.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.message)
    return res


@auth_router.post("/refresh", response_model=RefreshResponse, summary="Làm mới token phiên")
def refresh_endpoint(payload: RefreshRequest):
    """Làm mới Access Token khi hết hạn bằng Refresh Token."""
    res = refresh_proxy(payload.refresh_token)
    if not res.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=res.message)
    return res


@auth_router.get("/me", response_model=MeResponse, summary="Lấy thông tin người dùng hiện tại")
def me_endpoint(auth_data: tuple[UserContext, str] = Depends(get_current_user_and_token)):
    """Trả về thông tin UserContext của người dùng tương ứng với Bearer token."""
    user_ctx, _ = auth_data
    return MeResponse(success=True, user_context=user_ctx, message="OK")


# ── Chat Endpoints ───────────────────────────────────────────────────────────

@chat_router.post("/", response_model=ChatResponse, summary="Gửi tin nhắn hội thoại và gọi công cụ SGOD")
def chat_endpoint(
    payload: ChatRequest,
    auth_data: tuple[UserContext, str] = Depends(get_current_user_and_token),
):
    """Xử lý hội thoại qua Google Gemini AI và thực thi các tool SGOD tương ứng."""
    user_ctx, access_token = auth_data
    res = _chat_engine.process_chat(
        message=payload.message,
        user_ctx=user_ctx,
        access_token=access_token,
        refresh_token=payload.refresh_token,
        history=payload.history,
    )
    return res


@chat_router.post("/stream", summary="Gửi tin nhắn hội thoại dạng Server-Sent Events (SSE) streaming")
def chat_stream_endpoint(
    payload: ChatRequest,
    auth_data: tuple[UserContext, str] = Depends(get_current_user_and_token),
):
    """Xử lý hội thoại qua Google Gemini AI dạng stream SSE kèm tool execution và token usage."""
    user_ctx, access_token = auth_data
    generator = _chat_engine.process_chat_stream(
        message=payload.message,
        user_ctx=user_ctx,
        access_token=access_token,
        refresh_token=payload.refresh_token,
        history=payload.history,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Tools Discovery ──────────────────────────────────────────────────────────

@tools_router.get("/", summary="Khám phá danh mục công cụ được phép theo vai trò")
def list_available_tools(
    auth_data: tuple[UserContext, str] = Depends(get_current_user_and_token),
):
    """Trả về danh sách 22 tools SGOD mà vai trò của người dùng hiện tại được phép gọi."""
    user_ctx, _ = auth_data
    allowed = filter_tools_for_role(user_ctx.role)
    return {
        "role": user_ctx.role,
        "count": len(allowed),
        "tools": [t.get("function") for t in allowed],
    }
