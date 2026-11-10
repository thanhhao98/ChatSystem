"""Health check schema."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    sgod_gateway: str
    gemini_configured: bool
    gemini_model: str
