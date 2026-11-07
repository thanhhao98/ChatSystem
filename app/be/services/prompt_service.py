"""Preamble and prompt rendering service."""

from __future__ import annotations

from app.be.core import config
from app.be.schemas import UserContext


def render_preamble(user_ctx: UserContext) -> str:
    """Render prompts/system_preamble_v1.txt with slots {role}, {role_vi}, {full_name}, {user_id}.
    Uses str.replace slot by slot per Contract 1 (never str.format).
    """
    text = ""
    if config.PREAMBLE_PATH.is_file():
        text = config.PREAMBLE_PATH.read_text(encoding="utf-8")

    text = text.replace("{role}", user_ctx.role)
    text = text.replace("{role_vi}", user_ctx.role_vi or user_ctx.role)
    text = text.replace("{full_name}", user_ctx.full_name)
    text = text.replace("{user_id}", user_ctx.user_id)
    return text.strip()
