"""Shared utilities for MCP servers — HTTP, rate-limiting, retries."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_project_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(_ENV_PATH)


class RateLimiter:
    def __init__(self, calls_per_minute: int) -> None:
        self.interval = 60.0 / max(calls_per_minute, 1)
        self._last = 0.0

    def wait(self) -> None:
        now = time.time()
        gap = now - self._last
        if gap < self.interval:
            time.sleep(self.interval - gap)
        self._last = time.time()


class _RetryableHTTPError(Exception):
    """Only 5xx / network errors should be retried."""


def _should_retry(exc: BaseException) -> bool:
    return isinstance(exc, (_RetryableHTTPError, requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((_RetryableHTTPError,
                                   requests.exceptions.ConnectionError,
                                   requests.exceptions.Timeout)),
)
def http_get(url: str, params: dict | None = None,
             headers: dict | None = None, timeout: int = 30) -> dict:
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    if resp.status_code == 402:
        return {"error": "Paid endpoint — upgrade your plan to access this data.",
                "status": 402}
    if resp.status_code == 404:
        return {"error": "Endpoint not found or no data available.", "status": 404}
    if resp.status_code == 429:
        raise _RetryableHTTPError(f"Rate limited (429): {resp.text[:100]}")
    if 400 <= resp.status_code < 500:
        return {"error": f"Client error {resp.status_code}: {resp.text[:200]}",
                "status": resp.status_code}
    if resp.status_code >= 500:
        raise _RetryableHTTPError(f"Server error {resp.status_code}")
    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError):
        body = resp.text.strip()
        if not body:
            return {"error": "Empty response from API", "raw": ""}
        return {"error": "Non-JSON response", "raw": body[:2000]}


def tool_result(data: dict, source: str, tool: str, params: dict) -> str:
    """Standard JSON envelope returned from every MCP tool."""
    return json.dumps({
        "data": data,
        "metadata": {
            "source": source,
            "tool": tool,
            "params": params,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }, default=str)


def tool_error(error: str, source: str, tool: str, params: dict) -> str:
    return json.dumps({
        "error": error,
        "metadata": {
            "source": source,
            "tool": tool,
            "params": params,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }, default=str)
