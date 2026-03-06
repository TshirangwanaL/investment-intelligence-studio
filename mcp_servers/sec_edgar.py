"""Wrapper: SEC EDGAR — delegates to real MCP server via MCPClient."""

from __future__ import annotations

from mcp_servers.base import MCPToolResult
from mcp_servers.client import MCPClient

_SERVER = "mcp_filings_sec_edgar"


class SecEdgarMCP:
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

    def get_company_filings(self, cik: str) -> MCPToolResult:
        return self._call("get_company_filings", {"cik": cik})

    def get_company_facts(self, cik: str) -> MCPToolResult:
        return self._call("get_company_facts", {"cik": cik})

    def get_ticker_to_cik(self, ticker: str) -> MCPToolResult:
        return self._call("ticker_to_cik", {"ticker": ticker})

    def search_filings(self, query: str, date_range: str = "",
                       forms: str = "10-K,10-Q,8-K", limit: int = 20) -> MCPToolResult:
        return self._call("get_company_filings", {"cik": query})
