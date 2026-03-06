"""Wrapper: GDELT — delegates to real MCP server via MCPClient."""

from __future__ import annotations

from mcp_servers.base import MCPToolResult
from mcp_servers.client import MCPClient

_SERVER = "mcp_news_gdelt"


class GdeltMCP:
    SERVER_NAME = _SERVER

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

    def search_news(self, query: str, mode: str = "ArtList",
                    max_records: int = 50, timespan: str = "7d",
                    source_country: str = "") -> MCPToolResult:
        return self._call("search_news", {
            "query": query, "mode": mode,
            "max_records": max_records, "timespan": timespan,
        })

    def get_tone_timeline(self, query: str, timespan: str = "30d") -> MCPToolResult:
        return self._call("get_tone_timeline", {"query": query, "timespan": timespan})

    def get_volume_timeline(self, query: str, timespan: str = "30d") -> MCPToolResult:
        return self._call("get_volume_timeline", {"query": query, "timespan": timespan})

    def get_theme_news(self, theme: str, max_records: int = 30) -> MCPToolResult:
        return self._call("get_theme_news", {"theme": theme, "max_records": max_records})
