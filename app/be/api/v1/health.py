"""Health check API endpoint (/api/health)."""

from __future__ import annotations

from fastapi import APIRouter

from app.be.api.deps import get_chat_service
from app.be.core import config
from app.be.schemas import HealthResponse

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("", response_model=HealthResponse, summary="Kiểm tra trạng thái hệ thống", include_in_schema=False)
@router.get("/", response_model=HealthResponse, summary="Kiểm tra trạng thái hệ thống")
def health_check() -> HealthResponse:
    """Kiểm tra tình trạng hoạt động của máy chủ Backend và cấu hình kết nối."""
    chat_svc = get_chat_service()
    active_model = getattr(chat_svc.gemini, "_preferred_model", None) or getattr(chat_svc.gemini, "model", None) or config.GEMINI_MODEL
    return HealthResponse(
        status="ok",
        sgod_gateway=config.SGOD_BASE_URL,
        gemini_configured=bool(config.GEMINI_API_KEY),
        gemini_model=active_model,
    )
