"""Wrapper: Financial Modeling Prep — delegates to real MCP server via MCPClient."""

from __future__ import annotations

from mcp_servers.base import MCPToolResult
from mcp_servers.client import MCPClient

_SERVER = "mcp_events_fmp"


class FMPMCP:
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

    def get_earnings_calendar(self, from_date: str = "", to_date: str = "") -> MCPToolResult:
        return self._call("get_earnings_calendar", {
            "from_date": from_date, "to_date": to_date,
        })

    def get_earnings_calendar_for_ticker(self, symbol: str) -> MCPToolResult:
        return self._call("get_earnings_calendar", {"symbol": symbol})

    def get_earnings_transcript(self, symbol: str, year: int,
                                quarter: int) -> MCPToolResult:
        return self._call("get_earnings_transcript", {
            "symbol": symbol, "year": year, "quarter": quarter,
        })

    def get_press_releases(self, symbol: str, limit: int = 20) -> MCPToolResult:
        return self._call("get_press_releases", {"symbol": symbol, "limit": limit})

    def get_stock_peers(self, symbol: str) -> MCPToolResult:
        return self._call("get_stock_peers", {"symbol": symbol})

    def get_analyst_estimates(self, symbol: str, limit: int = 10) -> MCPToolResult:
        return self._call("get_analyst_estimates", {"symbol": symbol, "limit": limit})

    def get_company_profile(self, symbol: str) -> MCPToolResult:
        return self._call("get_company_profile", {"symbol": symbol})
