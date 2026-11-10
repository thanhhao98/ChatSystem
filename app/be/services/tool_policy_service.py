"""Tool catalog and role-based policy filtering service."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from app.be.core import config


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
