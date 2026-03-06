"""Wrapper: FRED — delegates to real MCP server via MCPClient."""

from __future__ import annotations

from typing import Any

from mcp_servers.base import MCPToolResult
from mcp_servers.client import MCPClient

_SERVER = "mcp_macro_fred"


class FredMCP:
    SERVER_NAME = _SERVER

    MACRO_SERIES = {
        "CPI": "CPIAUCSL", "CORE_CPI": "CPILFESL", "FED_FUNDS": "FEDFUNDS",
        "UNEMPLOYMENT": "UNRATE", "GDP": "GDP", "T10Y2Y": "T10Y2Y",
        "T10Y3M": "T10Y3M", "BAA_SPREAD": "BAAFFM", "VIX": "VIXCLS",
        "M2": "M2SL", "INITIAL_CLAIMS": "ICSA",
    }

    def __init__(self, client: MCPClient | None = None) -> None:
        self._client = client or MCPClient()

    def _call(self, tool: str, params: dict) -> MCPToolResult:
        raw = self._client.call_tool(_SERVER, tool, params)
        return MCPToolResult(
            data=raw.get("data", raw),
            source=_SERVER,
            tool_name=tool,
            query_params=params,
            error=raw.get("error", ""),
        )

    def get_series(self, series_id: str, observation_start: str = "",
                   observation_end: str = "", limit: int = 500) -> MCPToolResult:
        return self._call("get_series_observations", {
            "series_id": series_id, "limit": limit,
            "observation_start": observation_start,
            "observation_end": observation_end,
        })

    def get_series_info(self, series_id: str) -> MCPToolResult:
        return self._call("get_series_info", {"series_id": series_id})

    def search_series(self, search_text: str, limit: int = 20) -> MCPToolResult:
        return self._call("search_series", {"search_text": search_text, "limit": limit})

    def get_macro_dashboard(self) -> MCPToolResult:
        return self._call("get_macro_dashboard", {})
