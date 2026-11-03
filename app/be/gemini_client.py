"""Google Gemini Client module using OpenAI-compatible protocol.
Supports tool-calling, function definition passing, and smart fallback simulation.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from app.be import config


class GeminiClient:
    """Client for Google Gemini via OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 40.0,
    ) -> None:
        self.api_key = (api_key or config.GEMINI_API_KEY).strip()
        raw_base = (base_url or config.GEMINI_BASE_URL).rstrip("/")
        # Ensure standard /chat/completions path
        if not raw_base.endswith("/v1") and not raw_base.endswith("/openai"):
            raw_base += "/v1"
        self.base_url = raw_base
        self.model = model or config.GEMINI_MODEL
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Send chat completion request to Gemini.
        Returns: (choice_message_dict, error_text)
        """
        if not self.is_configured:
            # Fallback simulator when GEMINI_API_KEY is not yet supplied in .env
            return self._simulate_response(messages, tools)

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                raw = resp.read()
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            return None, f"Gemini API error (HTTP {e.code}): {err_msg[:200]}"
        except Exception as e:
            return None, f"Gemini network error: {type(e).__name__}"

        try:
            res_json = json.loads(raw.decode("utf-8"))
            choices = res_json.get("choices") or []
            if not choices:
                return None, "Gemini returned empty choices"
            msg = choices[0].get("message")
            return msg, None
        except Exception as e:
            return None, f"Failed to parse Gemini response: {e}"

    def _simulate_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Smart fallback for testing tool-calling loop offline or without a Gemini API key."""
        # Find latest user query
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = str(m.get("content") or "").lower()
                break

        # If previous message is a tool response, synthesize final text answer
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "tool":
            tool_content = last_msg.get("content", "")
            return {
                "role": "assistant",
                "content": f"Dựa trên dữ liệu hệ thống SGOD, đây là thông tin bạn yêu cầu:\n{tool_content[:400]}...",
            }, None

        # Detect intent and generate a mock tool_call
        if "tài sản" in user_msg or "asset" in user_msg:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_asset_1",
                        "type": "function",
                        "function": {
                            "name": "list_my_assets",
                            "arguments": json.dumps({"limit": 5}),
                        },
                    }
                ],
            }, None
        elif "doanh nghiệp" in user_msg or "công ty" in user_msg:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_ent_1",
                        "type": "function",
                        "function": {
                            "name": "get_enterprise_profile",
                            "arguments": "{}",
                        },
                    }
                ],
            }, None
        elif "địa điểm" in user_msg or "kho" in user_msg or "location" in user_msg:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_loc_1",
                        "type": "function",
                        "function": {
                            "name": "list_locations",
                            "arguments": json.dumps({"limit": 5}),
                        },
                    }
                ],
            }, None

        # General conversation fallback
        return {
            "role": "assistant",
            "content": "Xin chào! Tôi là trợ lý ảo SGOD. Bạn có thể hỏi tôi về danh sách tài sản, thông tin địa điểm lưu kho, lịch bảo trì hoặc hồ sơ doanh nghiệp.",
        }, None
