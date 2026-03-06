"""MCP Server: Internal Quant — safe compute only, whitelisted functions.

No arbitrary code execution. Only vetted quantitative functions.
Run standalone:  python mcp_servers/quant_server.py
"""

import json
import numpy as np
from mcp.server.fastmcp import FastMCP
from mcp_servers._shared import tool_result, tool_error

mcp = FastMCP(
    "mcp_quant",
    instructions="Internal safe-compute quant server: portfolio vol, correlation, Sharpe, drawdown, VaR, HHI",
)


@mcp.tool()
def portfolio_volatility(returns_json: str, weights_json: str) -> str:
    """Compute annualized portfolio volatility from asset returns and weights.

    Args:
        returns_json: JSON array of arrays — daily returns per asset [[r1_t1, r1_t2, ...], ...]
        weights_json: JSON array of portfolio weights [w1, w2, ...]
    """
    try:
        returns = np.array(json.loads(returns_json))
        weights = np.array(json.loads(weights_json))
        cov = np.cov(returns, rowvar=False)
        port_var = float(weights @ cov @ weights)
        return tool_result(
            {"annual_volatility": float(np.sqrt(port_var * 252)),
             "daily_volatility": float(np.sqrt(port_var))},
            "quant", "portfolio_volatility", {"n_assets": len(weights)})
    except Exception as e:
        return tool_error(str(e), "quant", "portfolio_volatility", {})


@mcp.tool()
def correlation_matrix(returns_json: str, tickers_json: str) -> str:
    """Compute pairwise correlation matrix from asset returns.

    Args:
        returns_json: JSON array of arrays — daily returns per asset
        tickers_json: JSON array of ticker names
    """
    try:
        ret = np.array(json.loads(returns_json))
        tickers = json.loads(tickers_json)
        corr = np.corrcoef(ret, rowvar=False)
        n = len(tickers)
        avg = float((corr.sum() - n) / (n * (n - 1))) if n > 1 else 0.0
        return tool_result(
            {"tickers": tickers, "matrix": corr.tolist(), "avg_correlation": avg},
            "quant", "correlation_matrix", {"tickers": tickers})
    except Exception as e:
        return tool_error(str(e), "quant", "correlation_matrix", {})


@mcp.tool()
def sharpe_ratio(returns_json: str, risk_free_rate: float = 0.04) -> str:
    """Compute annualized Sharpe ratio from daily returns.

    Args:
        returns_json: JSON array of daily returns
        risk_free_rate: Annual risk-free rate (default 4%)
    """
    try:
        ret = np.array(json.loads(returns_json))
        excess = ret - risk_free_rate / 252
        if ret.std() == 0:
            s = 0.0
        else:
            s = float(excess.mean() / ret.std() * np.sqrt(252))
        return tool_result({"sharpe": s}, "quant", "sharpe_ratio",
                           {"risk_free_rate": risk_free_rate})
    except Exception as e:
        return tool_error(str(e), "quant", "sharpe_ratio", {})


@mcp.tool()
def max_drawdown(prices_json: str) -> str:
    """Compute maximum drawdown from a price series.

    Args:
        prices_json: JSON array of prices
    """
    try:
        p = np.array(json.loads(prices_json))
        peak = np.maximum.accumulate(p)
        dd = (p - peak) / peak
        return tool_result(
            {"max_drawdown": float(dd.min()),
             "max_drawdown_pct": float(dd.min() * 100)},
            "quant", "max_drawdown", {"n_points": len(p)})
    except Exception as e:
        return tool_error(str(e), "quant", "max_drawdown", {})


@mcp.tool()
def var_historical(returns_json: str, confidence: float = 0.95) -> str:
    """Compute historical Value at Risk.

    Args:
        returns_json: JSON array of daily returns
        confidence: Confidence level (default 95%)
    """
    try:
        ret = np.array(json.loads(returns_json))
        var = float(np.percentile(ret, (1 - confidence) * 100))
        return tool_result({"var": var, "confidence": confidence},
                           "quant", "var_historical", {"confidence": confidence})
    except Exception as e:
        return tool_error(str(e), "quant", "var_historical", {})


@mcp.tool()
def concentration_hhi(weights_json: str) -> str:
    """Compute HHI concentration index and top-5 weight from portfolio weights.

    Args:
        weights_json: JSON array of portfolio weights
    """
    try:
        w = np.array(json.loads(weights_json))
        hhi = float(np.sum(w ** 2))
        top5 = float(sum(sorted(w, reverse=True)[:5]))
        return tool_result({"hhi": hhi, "top5_concentration": top5},
                           "quant", "concentration_hhi", {"n_positions": len(w)})
    except Exception as e:
        return tool_error(str(e), "quant", "concentration_hhi", {})


if __name__ == "__main__":
    mcp.run()
