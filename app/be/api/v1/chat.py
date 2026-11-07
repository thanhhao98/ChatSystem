"""Chat API endpoints (/api/chat)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.be.api.deps import get_chat_service, get_current_user_and_token
from app.be.schemas import ChatRequest, UserContext
from app.be.services import ChatService

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", summary="Gửi tin nhắn hội thoại dạng Server-Sent Events (SSE) streaming", include_in_schema=False)
@router.post("/", summary="Gửi tin nhắn hội thoại dạng Server-Sent Events (SSE) streaming", include_in_schema=False)
@router.post("/stream", summary="Gửi tin nhắn hội thoại dạng Server-Sent Events (SSE) streaming")
def chat_stream_endpoint(
    payload: ChatRequest,
    auth_data: tuple[UserContext, str] = Depends(get_current_user_and_token),
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Xử lý hội thoại qua Google Gemini AI dạng stream SSE kèm tool execution và token usage."""
    user_ctx, access_token = auth_data
    generator = chat_service.process_chat_stream(
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
