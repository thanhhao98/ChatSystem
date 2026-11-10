"""Core configuration and settings for ChatSystem Backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

# Repository root directory
REPO_ROOT: Path = Path(__file__).resolve().parents[3]
ENV_PATH: Path = REPO_ROOT / ".env"

# Auto-load .env into os.environ if present
if ENV_PATH.is_file():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v

# SGOD Gateway configuration
SGOD_BASE_URL: str = os.environ.get("SGOD_BASE_URL", "").rstrip("/")
SGOD_AUTH_API_KEY: str = os.environ.get("SGOD_AUTH_API_KEY", "").strip()
SGOD_ASSET_API_KEY: str = os.environ.get("SGOD_ASSET_API_KEY", "").strip()
SGOD_CHAT_API_KEY: str = os.environ.get("SGOD_CHAT_API_KEY", "").strip()

# Google Gemini configuration (via OpenAI-compatible endpoint)
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_BASE_URL: str = os.environ.get(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
).rstrip("/")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").strip()

# Internal paths
ROLES_PATH: Path = REPO_ROOT / "tools" / "sgod" / "roles.json"
TOOLS_PATH: Path = REPO_ROOT / "tools" / "sgod" / "sgod_tools.json"
POLICY_PATH: Path = REPO_ROOT / "tools" / "sgod" / "tool_policy.json"
PREAMBLE_PATH: Path = REPO_ROOT / "prompts" / "system_preamble_v1.txt"

SERVICE_KEYS: Dict[str, str] = {
    "auth": SGOD_AUTH_API_KEY,
    "asset": SGOD_ASSET_API_KEY,
    "chat": SGOD_CHAT_API_KEY,
}
