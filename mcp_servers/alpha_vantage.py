"""Wrapper: Alpha Vantage — delegates to real MCP server via MCPClient."""

from __future__ import annotations

from mcp_servers.base import MCPToolResult
from mcp_servers.client import MCPClient

_SERVER = "mcp_marketdata_alpha_vantage"


class AlphaVantageMCP:
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

    def get_daily(self, symbol: str, outputsize: str = "compact") -> MCPToolResult:
        return self._call("get_daily_prices", {"symbol": symbol, "outputsize": outputsize})

    def get_weekly(self, symbol: str) -> MCPToolResult:
        return self._call("get_weekly_prices", {"symbol": symbol})

    def get_quote(self, symbol: str) -> MCPToolResult:
        return self._call("get_quote", {"symbol": symbol})

    def get_sma(self, symbol: str, interval: str = "daily",
                time_period: int = 50, series_type: str = "close") -> MCPToolResult:
        return self._call("get_sma", {
            "symbol": symbol, "interval": interval,
            "time_period": time_period, "series_type": series_type,
        })

    def get_rsi(self, symbol: str, interval: str = "daily",
                time_period: int = 14, series_type: str = "close") -> MCPToolResult:
        return self._call("get_rsi", {
            "symbol": symbol, "interval": interval,
            "time_period": time_period, "series_type": series_type,
        })

    def get_macd(self, symbol: str, interval: str = "daily",
                 series_type: str = "close") -> MCPToolResult:
        return self._call("get_macd", {
            "symbol": symbol, "interval": interval, "series_type": series_type,
        })

    def get_overview(self, symbol: str) -> MCPToolResult:
        return self._call("get_company_overview", {"symbol": symbol})

    def search_symbol(self, keywords: str) -> MCPToolResult:
        return self._call("search_symbol", {"keywords": keywords})
