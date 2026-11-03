"""Agentic Chat Engine orchestrating conversation, prompt rendering,
tool policy filtering, Gemini interaction, and SGOD tool execution.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from app.be import config
from app.be.gemini_client import GeminiClient
from app.be.schemas import ChatMessage, ChatResponse, ToolExecutionRecord, UserContext
from tools.sgod.tool_executor import SGODToolExecutor


def load_tools_and_policy() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Load catalogue tools and policy dictionary."""
    tools: List[Dict[str, Any]] = []
    policy: Dict[str, Any] = {}

    if config.TOOLS_PATH.is_file():
        try:
            with config.TOOLS_PATH.open("r", encoding="utf-8") as f:
                tools = json.load(f)
        except Exception:
            pass

    if config.POLICY_PATH.is_file():
        try:
            with config.POLICY_PATH.open("r", encoding="utf-8") as f:
                policy = json.load(f)
        except Exception:
            pass

    return tools, policy


def filter_tools_for_role(user_role: str) -> List[Dict[str, Any]]:
    """Filter tools in sgod_tools.json based on tool_policy.json for the specified role.
    Converts each tool definition to OpenAI-compatible function calling format.
    """
    tools, policy = load_tools_and_policy()
    allowed_tools: List[Dict[str, Any]] = []

    for t in tools:
        fn = t.get("function") or {}
        name = fn.get("name")
        if not name:
            continue

        entry = policy.get(name) or {}
        allowed_roles = entry.get("roles") or []
        if user_role in allowed_roles:
            allowed_tools.append({
                "type": "function",
                "function": fn,
            })

    return allowed_tools


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


class ChatEngine:
    """Orchestrates LLM prompts, tool execution loop, and state management."""

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

    def process_chat(
        self,
        message: str,
        user_ctx: UserContext,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        history: Optional[List[ChatMessage]] = None,
        max_turns: int = 3,
    ) -> ChatResponse:
        """Run complete Agentic Tool-calling loop."""
        # 1. Filter tools and render system prompt
        allowed_tools = filter_tools_for_role(user_ctx.role)
        preamble = render_preamble(user_ctx)

        # 2. Build messages array
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

        final_reply = ""

        # 3. Agentic Loop (up to max_turns)
        for _ in range(max_turns):
            assistant_msg, err = self.gemini.chat_completion(
                messages=messages,
                tools=allowed_tools if allowed_tools else None,
                temperature=0.0,
            )

            if err:
                return ChatResponse(
                    success=False,
                    reply=f"Xin lỗi, đã xảy ra lỗi khi kết nối với mô hình AI: {err}",
                    tools_executed=executed_records,
                )

            if not assistant_msg:
                break

            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                # Direct text response from LLM
                final_reply = assistant_msg.get("content") or ""
                break

            # LLM requested tool calling
            messages.append(assistant_msg)

            for tc in tool_calls:
                fn = tc.get("function") or {}
                t_name = fn.get("name")
                raw_args = fn.get("arguments") or "{}"

                try:
                    args_dict = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args_dict = {}

                # Execute against live SGOD Gateway
                result = self.executor.execute(
                    tool_name=t_name,
                    arguments=args_dict,
                    user_role=user_ctx.role,
                    access_token=cur_token,
                    refresh_token=refresh_token,
                )

                if result.token_refreshed:
                    token_refreshed = True
                    new_access = result.new_access_token
                    cur_token = result.new_access_token

                executed_records.append(
                    ToolExecutionRecord(
                        tool_name=t_name,
                        arguments=args_dict,
                        result=result.data if result.success else None,
                        success=result.success,
                        error=result.error or result.message,
                    )
                )

                # Feed tool result back to LLM
                tool_output_str = json.dumps(result.to_dict(), ensure_ascii=False)
                messages.append({
                    "role": "tool",
                    "name": t_name,
                    "tool_call_id": tc.get("id") or f"call_{t_name}",
                    "content": tool_output_str,
                })

        if not final_reply and executed_records:
            # Fallback text if loop ended
            success_count = sum(1 for r in executed_records if r.success)
            final_reply = f"Đã hoàn thành gọi {len(executed_records)} công cụ ({success_count} thành công)."

        return ChatResponse(
            success=True,
            reply=final_reply,
            tools_executed=executed_records,
            token_refreshed=token_refreshed,
            new_access_token=new_access,
        )
