"""API v1 routers."""

from __future__ import annotations

from app.be.api.v1.auth import router as auth_router
from app.be.api.v1.chat import router as chat_router
from app.be.api.v1.health import router as health_router
from app.be.api.v1.tools import router as tools_router

__all__ = ["auth_router", "chat_router", "tools_router", "health_router"]
