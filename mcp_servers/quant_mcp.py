"""Wrapper: Internal Quant — delegates to real MCP server via MCPClient."""

from __future__ import annotations

import json

from mcp_servers.base import MCPToolResult
from mcp_servers.client import MCPClient

_SERVER = "mcp_quant"


class QuantMCP:
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

    def portfolio_volatility(self, returns: list[list[float]],
                             weights: list[float]) -> MCPToolResult:
        return self._call("portfolio_volatility", {
            "returns_json": json.dumps(returns),
            "weights_json": json.dumps(weights),
        })

    def correlation_matrix(self, returns: list[list[float]],
                           tickers: list[str]) -> MCPToolResult:
        return self._call("correlation_matrix", {
            "returns_json": json.dumps(returns),
            "tickers_json": json.dumps(tickers),
        })

    def sharpe_ratio(self, returns: list[float],
                     risk_free_rate: float = 0.04) -> MCPToolResult:
        return self._call("sharpe_ratio", {
            "returns_json": json.dumps(returns),
            "risk_free_rate": risk_free_rate,
        })

    def max_drawdown(self, prices: list[float]) -> MCPToolResult:
        return self._call("max_drawdown", {
            "prices_json": json.dumps(prices),
        })

    def var_historical(self, returns: list[float],
                       confidence: float = 0.95) -> MCPToolResult:
        return self._call("var_historical", {
            "returns_json": json.dumps(returns),
            "confidence": confidence,
        })

    def concentration_hhi(self, weights: list[float]) -> MCPToolResult:
        return self._call("concentration_hhi", {
            "weights_json": json.dumps(weights),
        })
