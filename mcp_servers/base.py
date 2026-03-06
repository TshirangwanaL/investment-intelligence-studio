"""MCPToolResult — the standard result envelope used by wrapper classes.

The actual MCP server logic lives in the *_server.py files (FastMCP).
The wrapper classes (alpha_vantage.py, fred.py, …) delegate through MCPClient
and return MCPToolResult for backward compatibility with agents and UI code.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class MCPToolResult:
    """Standard result envelope for every MCP tool call."""

    def __init__(
        self,
        data: Any = None,
        source: str = "",
        tool_name: str = "",
        query_params: dict | None = None,
        timestamp: str | None = None,
        cached: bool = False,
        error: str = "",
    ):
        self.data = data or {}
        self.source = source
        self.tool_name = tool_name
        self.query_params = query_params or {}
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.cached = cached
        self.error = error
        self.success = not bool(error)

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "metadata": {
                "source": self.source,
                "tool_name": self.tool_name,
                "query_params": self.query_params,
                "timestamp": self.timestamp,
                "cached": self.cached,
            },
            "success": self.success,
            "error": self.error,
        }
