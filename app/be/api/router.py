"""Central API Router aggregating all domain sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.be.api.v1 import (
    auth_router,
    chat_router,
    health_router,
    tools_router,
)

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(tools_router)
api_router.include_router(health_router)

__all__ = ["api_router", "auth_router", "chat_router", "tools_router", "health_router"]
