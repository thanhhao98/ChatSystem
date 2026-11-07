"""Chat, message history, and tool execution schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', 'system', hoặc 'tool'")
    content: Optional[str] = Field(None, description="Nội dung tin nhắn")
    name: Optional[str] = Field(None, description="Tên công cụ (khi role là 'tool')")
    tool_call_id: Optional[str] = Field(None, description="ID của lệnh gọi công cụ")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Nội dung câu hỏi của người dùng")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Lịch sử hội thoại trước đó (nếu có)")
    refresh_token: Optional[str] = Field(None, description="Refresh token dự phòng khi thực thi công cụ SGOD")


class ToolExecutionRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    status_code: Optional[int] = Field(None, description="Mã phản hồi HTTP từ SGOD Gateway")
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ChatResponse(BaseModel):
    success: bool
    reply: str
    tools_executed: List[ToolExecutionRecord] = Field(default_factory=list)
    token_refreshed: bool = False
    new_access_token: Optional[str] = None
    message: Optional[str] = None
    response_time_ms: Optional[int] = None
    token_usage: Optional[Dict[str, int]] = None
