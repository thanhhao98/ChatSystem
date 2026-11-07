"""FastAPI dependency injection utilities."""

from __future__ import annotations

from typing import Generator
from app.be.core import get_current_user_and_token
from app.be.services import AuthService, ChatService

# Default service instances
_auth_service = AuthService()
_chat_service = ChatService()


def get_auth_service() -> AuthService:
    """Dependency providing AuthService instance."""
    return _auth_service


def get_chat_service() -> ChatService:
    """Dependency providing ChatService instance."""
    return _chat_service


__all__ = [
    "get_current_user_and_token",
    "get_auth_service",
    "get_chat_service",
]
