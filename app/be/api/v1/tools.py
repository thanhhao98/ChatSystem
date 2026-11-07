"""Tools discovery API endpoints (/api/tools)."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends

from app.be.api.deps import get_current_user_and_token
from app.be.schemas import UserContext
from app.be.services import filter_tools_for_role

router = APIRouter(prefix="/api/tools", tags=["Tools"])


@router.get("", summary="Khám phá danh mục công cụ được phép theo vai trò", include_in_schema=False)
@router.get("/", summary="Khám phá danh mục công cụ được phép theo vai trò")
def list_available_tools(
    auth_data: tuple[UserContext, str] = Depends(get_current_user_and_token),
) -> Dict[str, Any]:
    """Trả về danh sách 22 tools SGOD mà vai trò của người dùng hiện tại được phép gọi."""
    user_ctx, _ = auth_data
    allowed = filter_tools_for_role(user_ctx.role)
    return {
        "role": user_ctx.role,
        "count": len(allowed),
        "tools": [t.get("function") for t in allowed],
    }
