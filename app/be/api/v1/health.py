"""Health check API endpoint (/api/health)."""

from __future__ import annotations

from fastapi import APIRouter

from app.be.core import config
from app.be.schemas import HealthResponse

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("", response_model=HealthResponse, summary="Kiểm tra trạng thái hệ thống", include_in_schema=False)
@router.get("/", response_model=HealthResponse, summary="Kiểm tra trạng thái hệ thống")
def health_check() -> HealthResponse:
    """Kiểm tra tình trạng hoạt động của máy chủ Backend và cấu hình kết nối."""
    return HealthResponse(
        status="ok",
        sgod_gateway=config.SGOD_BASE_URL,
        gemini_configured=bool(config.GEMINI_API_KEY),
        gemini_model=config.GEMINI_MODEL,
    )
