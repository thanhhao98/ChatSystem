"""Agentic Chat Service orchestrating conversation, prompt rendering,
tool policy filtering, Gemini streaming, and SGOD tool execution.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Generator, List, Optional

from app.be.clients import GeminiClient
from app.be.core import config
from app.be.schemas import (
    ChatMessage,
    ToolExecutionRecord,
    UserContext,
)
from app.be.services.prompt_service import render_preamble
from app.be.services.tool_policy_service import filter_tools_for_role
from tools.sgod.tool_executor import SGODToolExecutor


_LLM_NOISE_ITEM_KEYS = {
    "qrCode",
    "images",
    "files",
    "enterpriseId",
    "categoryId",
    "createdBy",
    "createdAt",
    "updatedAt",
    "locations",
    "onBlockchain",
    "verifyTransfer",
    "typeEncrypt",
    "_importanceLevel",
    "fromElasticsearch",
    "_fromElasticsearch",
}


def _compact_tool_dict_for_llm(raw_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal hashes/IDs from LLM tool context while preserving all business fields.
    Does not mutate raw_dict (which is sent in full to the frontend ToolExecutionRecord).
    """
    data = raw_dict.get("data")
    if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
        return raw_dict

    compact_items = []
    for item in data["items"]:
        if isinstance(item, dict):
            compact_items.append({
                k: v for k, v in item.items()
                if k not in _LLM_NOISE_ITEM_KEYS and v is not None and v != []
            })
        else:
            compact_items.append(item)

    compact_data: Dict[str, Any] = {"items": compact_items}
    if isinstance(data.get("meta"), dict):
        meta = data["meta"]
        compact_data["meta"] = {
            k: v for k, v in meta.items() if k in ("hasNextPage", "limit", "total")
        }

    return {
        "success": raw_dict.get("success", True),
        "status_code": raw_dict.get("status_code", 200),
        "data": compact_data,
    }


class ChatService:
    """Orchestrates LLM streaming prompts, tool execution loop, and state management."""

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        tool_executor: Optional[SGODToolExecutor] = None,
    ) -> None:
        self.gemini = gemini_client or GeminiClient()
        self.executor = tool_executor or SGODToolExecutor(
            base_url=config.SGOD_BASE_URL,
            auth_key=config.SGOD_AUTH_API_KEY,
            asset_key=config.SGOD_ASSET_API_KEY,
            chat_key=config.SGOD_CHAT_API_KEY,
            tools_path=config.TOOLS_PATH,
            policy_path=config.POLICY_PATH,
        )

    def process_chat_stream(
        self,
        message: str,
        user_ctx: UserContext,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None,
        max_turns: int = 3,
    ) -> Generator[str, None, None]:
        """Run complete Agentic Tool-calling loop with Server-Sent Events (SSE) streaming."""
        start_time = time.time()
        allowed_tools = filter_tools_for_role(user_ctx.role)
        preamble = render_preamble(user_ctx)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": preamble}
        ]

        if history:
            for h in history:
                m: Dict[str, Any] = {"role": h.role, "content": h.content or ""}
                if h.name:
                    m["name"] = h.name
                if h.tool_call_id:
                    m["tool_call_id"] = h.tool_call_id
                messages.append(m)

        messages.append({"role": "user", "content": message})

        executed_records: List[ToolExecutionRecord] = []
        token_refreshed = False
        new_access = None
        cur_token = access_token
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        final_reply = ""

        yield f"event: status\ndata: {json.dumps({'message': 'Đang phân tích yêu cầu...'}, ensure_ascii=False)}\n\n"

        for turn in range(max_turns):
            tool_calls = None
            stream_error = None
            turn_reply = ""
            turn_usage: Optional[Dict[str, int]] = None

            for ev_type, data in self.gemini.chat_completion_stream(
                messages=messages,
                tools=allowed_tools if allowed_tools else None,
                temperature=0.0,
            ):
                if ev_type == "error":
                    stream_error = data
                    break
                elif ev_type == "usage":
                    turn_usage = data
                elif ev_type == "tool_calls":
                    tool_calls = data
                elif ev_type == "delta":
                    turn_reply += data
                    final_reply += data
                    yield f"event: delta\ndata: {json.dumps({'content': data}, ensure_ascii=False)}\n\n"

            if turn_usage:
                total_tokens["prompt_tokens"] += turn_usage.get("prompt_tokens", 0)
                total_tokens["completion_tokens"] += turn_usage.get("completion_tokens", 0)
                total_tokens["total_tokens"] += turn_usage.get("total_tokens", 0)

            if stream_error:
                yield f"event: error\ndata: {json.dumps({'error': stream_error}, ensure_ascii=False)}\n\n"
                return

            if not tool_calls:
                break

            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": turn_reply or None,
                "tool_calls": tool_calls,
            }
            for tc in tool_calls:
                if tc.get("extra_content"):
                    assistant_msg["extra_content"] = tc["extra_content"]
                    break
            messages.append(assistant_msg)

            for tc in tool_calls:
                fn = tc.get("function") or {}
                t_name = fn.get("name")
                raw_args = fn.get("arguments") or "{}"
                try:
                    args_dict = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args_dict = {}

                yield f"event: tool_start\ndata: {json.dumps({'tool_name': t_name, 'arguments': args_dict}, ensure_ascii=False)}\n\n"

                t0 = time.time()
                result = self.executor.execute(
                    tool_name=t_name,
                    arguments=args_dict,
                    user_role=user_ctx.role,
                    access_token=cur_token,
                    refresh_token=refresh_token,
                )
                dur_ms = int((time.time() - t0) * 1000)

                if result.token_refreshed:
                    token_refreshed = True
                    new_access = result.new_access_token
                    cur_token = result.new_access_token

                record = ToolExecutionRecord(
                    tool_name=t_name,
                    arguments=args_dict,
                    result=result.data if result.success else None,
                    success=result.success,
                    status_code=result.status_code,
                    error=(result.error or result.message) if not result.success else None,
                    duration_ms=dur_ms,
                )
                executed_records.append(record)

                yield f"event: tool_result\ndata: {json.dumps(record.model_dump() if hasattr(record, 'model_dump') else record.dict(), ensure_ascii=False)}\n\n"

                llm_payload = _compact_tool_dict_for_llm(result.to_dict())
                tool_output_str = json.dumps(llm_payload, ensure_ascii=False)
                messages.append({
                    "role": "tool",
                    "name": t_name,
                    "tool_call_id": tc.get("id") or f"call_{t_name}",
                    "content": tool_output_str,
                })

            yield f"event: status\ndata: {json.dumps({'message': 'Đang tổng hợp câu trả lời từ dữ liệu SGOD...'}, ensure_ascii=False)}\n\n"

        total_duration_ms = int((time.time() - start_time) * 1000)
        tools_dict_list = [
            r.model_dump() if hasattr(r, 'model_dump') else r.dict()
            for r in executed_records
        ]

        active_model = getattr(self.gemini, "_preferred_model", None) or getattr(self.gemini, "model", None) or config.GEMINI_MODEL
        yield f"event: done\ndata: {json.dumps({'reply': final_reply, 'model': active_model, 'tools_executed': tools_dict_list, 'response_time_ms': total_duration_ms, 'token_usage': total_tokens, 'token_refreshed': token_refreshed, 'new_access_token': new_access}, ensure_ascii=False)}\n\n"


# Alias ChatEngine for backward compatibility
ChatEngine = ChatService
