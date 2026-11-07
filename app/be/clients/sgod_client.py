"""Client for interacting with SGOD Gateway API endpoints."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from app.be.core import config


class SGODClient:
    """HTTP client communicating with SGOD Gateway services."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_api_key: Optional[str] = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or config.SGOD_BASE_URL).rstrip("/")
        self.auth_api_key = auth_api_key or config.SGOD_AUTH_API_KEY
        self.timeout = timeout

    def send_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
        """Dispatch HTTP request to SGOD Gateway.
        Returns: (status_code, json_dict, error_string)
        """
        url = self.base_url + path
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.auth_api_key,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        data_bytes = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

        eff_timeout = timeout if timeout is not None else self.timeout
        try:
            with urllib.request.urlopen(req, timeout=eff_timeout) as resp:
                status = resp.status
                raw = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            raw = e.read()
        except Exception as e:
            return 0, None, f"network_error: {type(e).__name__}"

        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
            return status, parsed, None
        except Exception:
            return status, None, "non_json_body"


# Default client instance
default_sgod_client = SGODClient()


def send_sgod_request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    timeout: float = 15.0,
) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
    """Convenience helper dispatching request using default client."""
    return default_sgod_client.send_request(
        method=method, path=path, body=body, token=token, timeout=timeout
    )
