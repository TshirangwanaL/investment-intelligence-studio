"""MCP Server: Market Data — OHLC, technicals, company overview (read-only).

Powered by yfinance (no API key required).
Run standalone:  python mcp_servers/alpha_vantage_server.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import yfinance as yf
from mcp.server.fastmcp import FastMCP
from mcp_servers._shared import load_project_env, tool_result, tool_error

load_project_env()

mcp = FastMCP(
    "mcp_marketdata_alpha_vantage",
    instructions="Read-only market data: daily/weekly OHLC, SMA, RSI, MACD, company overview",
)


def _sym(symbol: str) -> str:
    return symbol.strip().upper().replace(".", "-")


def _ohlc_records(df, limit: int = 100) -> list[dict]:
    if df is None or df.empty:
        return []
    df = df.copy().tail(limit)
    records = []
    for dt, row in df.iterrows():
        ts = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
        records.append({
            "date": ts,
            "open": round(float(row.get("Open", 0)), 4),
            "high": round(float(row.get("High", 0)), 4),
            "low": round(float(row.get("Low", 0)), 4),
            "close": round(float(row.get("Close", 0)), 4),
            "volume": int(row.get("Volume", 0)),
        })
    return records


@mcp.tool()
def get_daily_prices(symbol: str, outputsize: str = "compact") -> str:
    """Get daily OHLC time series for a stock symbol.

    Args:
        symbol: Ticker (e.g. AAPL, MSFT)
        outputsize: 'compact' (100 days) or 'full' (2 years)
    """
    try:
        period = "2y" if outputsize == "full" else "6mo"
        limit = 500 if outputsize == "full" else 100
        ticker = yf.Ticker(_sym(symbol))
        hist = ticker.history(period=period, interval="1d")
        records = _ohlc_records(hist, limit=limit)
        return tool_result(
            {"symbol": symbol, "time_series": records, "count": len(records)},
            "yfinance", "get_daily_prices",
            {"symbol": symbol, "outputsize": outputsize},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_daily_prices",
                          {"symbol": symbol, "outputsize": outputsize})


@mcp.tool()
def get_weekly_prices(symbol: str) -> str:
    """Get weekly OHLC time series for a stock symbol."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        hist = ticker.history(period="2y", interval="1wk")
        records = _ohlc_records(hist, limit=200)
        return tool_result(
            {"symbol": symbol, "time_series": records, "count": len(records)},
            "yfinance", "get_weekly_prices", {"symbol": symbol},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_weekly_prices", {"symbol": symbol})


@mcp.tool()
def get_quote(symbol: str) -> str:
    """Get the latest price quote for a symbol."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        info = ticker.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose", 0)
        change = price - prev if price and prev else 0
        pct = (change / prev * 100) if prev else 0
        quote = {
            "symbol": symbol,
            "price": round(price, 4) if price else 0,
            "change": round(change, 4),
            "change_percent": round(pct, 4),
            "volume": info.get("volume") or info.get("regularMarketVolume", 0),
            "high": info.get("dayHigh") or info.get("regularMarketDayHigh", 0),
            "low": info.get("dayLow") or info.get("regularMarketDayLow", 0),
            "open": info.get("open") or info.get("regularMarketOpen", 0),
            "previous_close": prev,
            "market_cap": info.get("marketCap", 0),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
        }
        return tool_result(quote, "yfinance", "get_quote", {"symbol": symbol})
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_quote", {"symbol": symbol})


def _compute_sma(closes: np.ndarray, period: int) -> list[float]:
    if len(closes) < period:
        return []
    result = []
    for i in range(period - 1, len(closes)):
        result.append(round(float(np.mean(closes[i - period + 1: i + 1])), 4))
    return result


def _compute_rsi(closes: np.ndarray, period: int = 14) -> list[float]:
    if len(closes) < period + 1:
        return []
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    rsi_values = []
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi_values.append(round(100 - (100 / (1 + rs)), 4))
    return rsi_values


def _compute_macd(closes: np.ndarray) -> dict:
    if len(closes) < 35:
        return {}

    def ema(data, span):
        alpha = 2 / (span + 1)
        out = [float(data[0])]
        for v in data[1:]:
            out.append(alpha * float(v) + (1 - alpha) * out[-1])
        return np.array(out)

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = ema12 - ema26
    signal = ema(macd_line, 9)
    histogram = macd_line - signal
    return {
        "macd": [round(float(v), 4) for v in macd_line[-20:]],
        "signal": [round(float(v), 4) for v in signal[-20:]],
        "histogram": [round(float(v), 4) for v in histogram[-20:]],
        "latest_macd": round(float(macd_line[-1]), 4),
        "latest_signal": round(float(signal[-1]), 4),
        "latest_histogram": round(float(histogram[-1]), 4),
    }


@mcp.tool()
def get_sma(symbol: str, interval: str = "daily",
            time_period: int = 50, series_type: str = "close") -> str:
    """Get Simple Moving Average (SMA) technical indicator."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        hist = ticker.history(period="1y", interval="1d")
        closes = hist["Close"].dropna().values
        sma = _compute_sma(closes, time_period)
        dates = [d.strftime("%Y-%m-%d") for d in hist.index[-len(sma):]]
        points = [{"date": d, "sma": v} for d, v in zip(dates, sma)]
        return tool_result(
            {"symbol": symbol, "time_period": time_period,
             "sma": points[-30:], "latest": sma[-1] if sma else None},
            "yfinance", "get_sma",
            {"symbol": symbol, "time_period": time_period},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_sma", {"symbol": symbol})


@mcp.tool()
def get_rsi(symbol: str, interval: str = "daily",
            time_period: int = 14, series_type: str = "close") -> str:
    """Get Relative Strength Index (RSI) technical indicator."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        hist = ticker.history(period="6mo", interval="1d")
        closes = hist["Close"].dropna().values
        rsi = _compute_rsi(closes, time_period)
        dates = [d.strftime("%Y-%m-%d") for d in hist.index[-(len(rsi)):]]
        points = [{"date": d, "rsi": v} for d, v in zip(dates, rsi)]
        latest = rsi[-1] if rsi else None
        signal = "overbought" if latest and latest > 70 else "oversold" if latest and latest < 30 else "neutral"
        return tool_result(
            {"symbol": symbol, "time_period": time_period,
             "rsi": points[-30:], "latest": latest, "signal": signal},
            "yfinance", "get_rsi",
            {"symbol": symbol, "time_period": time_period},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_rsi", {"symbol": symbol})


@mcp.tool()
def get_macd(symbol: str, interval: str = "daily",
             series_type: str = "close") -> str:
    """Get MACD technical indicator."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        hist = ticker.history(period="6mo", interval="1d")
        closes = hist["Close"].dropna().values
        macd_data = _compute_macd(closes)
        if not macd_data:
            return tool_error("Insufficient data for MACD", "yfinance", "get_macd",
                              {"symbol": symbol})
        return tool_result(
            {"symbol": symbol, **macd_data},
            "yfinance", "get_macd", {"symbol": symbol},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_macd", {"symbol": symbol})


@mcp.tool()
def get_company_overview(symbol: str) -> str:
    """Get fundamental company overview (PE, market cap, sector, etc.)."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        info = ticker.info or {}
        overview = {
            "symbol": symbol,
            "name": info.get("shortName") or info.get("longName", symbol),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap", 0),
            "pe_trailing": info.get("trailingPE"),
            "pe_forward": info.get("forwardPE"),
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "revenue": info.get("totalRevenue", 0),
            "profit_margin": info.get("profitMargins"),
            "return_on_equity": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "description": (info.get("longBusinessSummary") or "")[:500],
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", "USD"),
        }
        return tool_result(overview, "yfinance", "get_company_overview",
                           {"symbol": symbol})
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_company_overview",
                          {"symbol": symbol})


@mcp.tool()
def search_symbol(keywords: str) -> str:
    """Search for a stock symbol by keywords."""
    try:
        results = []
        for sym in [keywords.upper().strip()]:
            try:
                t = yf.Ticker(sym.replace(".", "-"))
                info = t.info or {}
                if info.get("shortName") or info.get("symbol"):
                    results.append({
                        "symbol": info.get("symbol", sym),
                        "name": info.get("shortName") or info.get("longName", ""),
                        "type": info.get("quoteType", ""),
                        "exchange": info.get("exchange", ""),
                    })
            except Exception:
                pass
        return tool_result(
            {"results": results, "count": len(results)},
            "yfinance", "search_symbol", {"keywords": keywords},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "search_symbol", {"keywords": keywords})


if __name__ == "__main__":
    mcp.run()
