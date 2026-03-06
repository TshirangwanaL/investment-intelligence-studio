"""MCP Server: Earnings & Fundamentals — earnings, profiles, peers (read-only).

Powered by yfinance (no API key required).
Run standalone:  python mcp_servers/fmp_server.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import yfinance as yf
from mcp.server.fastmcp import FastMCP
from mcp_servers._shared import load_project_env, tool_result, tool_error

load_project_env()

mcp = FastMCP(
    "mcp_events_fmp",
    instructions="Read-only earnings and fundamental data: calendar, profiles, peers, analyst estimates",
)


def _sym(symbol: str) -> str:
    return symbol.strip().upper().replace(".", "-")


@mcp.tool()
def get_earnings_calendar(symbol: str = "", from_date: str = "",
                          to_date: str = "") -> str:
    """Get earnings calendar and history for a symbol.

    Args:
        symbol: Ticker filter (e.g. AAPL)
        from_date: Start date (YYYY-MM-DD) — unused, kept for compatibility
        to_date: End date (YYYY-MM-DD) — unused, kept for compatibility
    """
    try:
        if not symbol:
            return tool_result(
                {"earnings": [], "note": "Provide a symbol for earnings data"},
                "yfinance", "get_earnings_calendar", {"symbol": symbol},
            )
        ticker = yf.Ticker(_sym(symbol))
        result: dict = {"symbol": symbol}

        try:
            cal = ticker.calendar
            if cal is not None:
                if isinstance(cal, dict):
                    result["upcoming"] = cal
                else:
                    result["upcoming"] = cal.to_dict() if hasattr(cal, "to_dict") else {}
        except Exception:
            result["upcoming"] = {}

        try:
            qe = ticker.quarterly_earnings
            if qe is not None and not qe.empty:
                records = qe.reset_index().to_dict("records")
                result["quarterly_earnings"] = records
        except Exception:
            pass

        try:
            ae = ticker.earnings
            if ae is not None and not ae.empty:
                result["annual_earnings"] = ae.reset_index().to_dict("records")
        except Exception:
            pass

        return tool_result(result, "yfinance", "get_earnings_calendar",
                           {"symbol": symbol})
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_earnings_calendar",
                          {"symbol": symbol})


@mcp.tool()
def get_earnings_transcript(symbol: str, year: int, quarter: int) -> str:
    """Get earnings call transcript for a specific quarter.

    Note: Full transcripts are not available via yfinance.
    Returns available earnings data and recent news as a substitute.

    Args:
        symbol: Ticker (e.g. AAPL)
        year: Fiscal year
        quarter: Quarter (1-4)
    """
    try:
        ticker = yf.Ticker(_sym(symbol))
        result: dict = {
            "symbol": symbol, "year": year, "quarter": quarter,
            "note": "Full transcripts unavailable — showing earnings data and recent news",
        }

        try:
            qe = ticker.quarterly_earnings
            if qe is not None and not qe.empty:
                result["quarterly_earnings"] = qe.reset_index().to_dict("records")
        except Exception:
            pass

        try:
            news = ticker.news or []
            result["recent_news"] = [
                {
                    "title": (item.get("content", {}) or {}).get("title") or item.get("title", ""),
                    "published": (item.get("content", {}) or {}).get("pubDate", ""),
                }
                for item in news[:5]
            ]
        except Exception:
            pass

        return tool_result(result, "yfinance", "get_earnings_transcript",
                           {"symbol": symbol, "year": year, "quarter": quarter})
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_earnings_transcript",
                          {"symbol": symbol})


@mcp.tool()
def get_company_profile(symbol: str) -> str:
    """Get company profile (market cap, sector, description, etc.)."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        info = ticker.info or {}
        profile = {
            "symbol": symbol,
            "companyName": info.get("shortName") or info.get("longName", symbol),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "description": (info.get("longBusinessSummary") or "")[:600],
            "price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
            "marketCap": info.get("marketCap", 0),
            "beta": info.get("beta"),
            "volAvg": info.get("averageVolume", 0),
            "mktCap": info.get("marketCap", 0),
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", "USD"),
            "country": info.get("country", ""),
            "fullTimeEmployees": info.get("fullTimeEmployees"),
            "website": info.get("website", ""),
            "ceo": info.get("companyOfficers", [{}])[0].get("name", "")
                   if info.get("companyOfficers") else "",
        }
        return tool_result([profile], "yfinance", "get_company_profile",
                           {"symbol": symbol})
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_company_profile",
                          {"symbol": symbol})


@mcp.tool()
def get_stock_peers(symbol: str) -> str:
    """Get peer companies for a stock (same sector/industry via yfinance)."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        info = ticker.info or {}
        sector = info.get("sector", "")
        industry = info.get("industry", "")

        _SECTOR_PEERS = {
            "Technology": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "CRM", "ORCL", "ADBE", "INTC"],
            "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "USB"],
            "Healthcare": ["JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT", "DHR", "BMY"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "LOW", "TJX", "BKNG", "GM"],
            "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
            "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA"],
            "Industrials": ["CAT", "UNP", "HON", "UPS", "GE", "BA", "RTX", "LMT", "DE", "MMM"],
            "Consumer Defensive": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "MDLZ", "EL"],
        }
        peers = _SECTOR_PEERS.get(sector, [])
        peers = [p for p in peers if p.upper() != symbol.upper()][:8]

        return tool_result(
            {"symbol": symbol, "sector": sector, "industry": industry,
             "peers": peers},
            "yfinance", "get_stock_peers", {"symbol": symbol},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_stock_peers", {"symbol": symbol})


@mcp.tool()
def get_analyst_estimates(symbol: str, limit: int = 10) -> str:
    """Get analyst consensus estimates and recommendations."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        info = ticker.info or {}
        result: dict = {"symbol": symbol}

        result["target_prices"] = {
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "target_mean": info.get("targetMeanPrice"),
            "target_median": info.get("targetMedianPrice"),
            "number_of_analysts": info.get("numberOfAnalystOpinions"),
            "recommendation": info.get("recommendationKey", ""),
            "recommendation_mean": info.get("recommendationMean"),
        }

        result["eps"] = {
            "trailing": info.get("trailingEps"),
            "forward": info.get("forwardEps"),
        }

        result["revenue"] = {
            "total": info.get("totalRevenue"),
            "growth": info.get("revenueGrowth"),
            "per_share": info.get("revenuePerShare"),
        }

        try:
            recs = ticker.recommendations
            if recs is not None and not recs.empty:
                recent = recs.tail(limit).reset_index().to_dict("records")
                result["recent_recommendations"] = recent
        except Exception:
            pass

        return tool_result(result, "yfinance", "get_analyst_estimates",
                           {"symbol": symbol, "limit": limit})
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_analyst_estimates",
                          {"symbol": symbol})


@mcp.tool()
def get_press_releases(symbol: str, limit: int = 20) -> str:
    """Get recent news/press releases for a company."""
    try:
        ticker = yf.Ticker(_sym(symbol))
        raw_news = ticker.news or []
        articles = []
        for item in raw_news[:limit]:
            content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
            pub = content.get("provider", {})
            articles.append({
                "title": content.get("title") or item.get("title", "Untitled"),
                "url": content.get("canonicalUrl", {}).get("url", "") or item.get("link", ""),
                "publisher": pub.get("displayName", "") if isinstance(pub, dict) else str(pub),
                "date": content.get("pubDate", "") or item.get("published", ""),
                "summary": content.get("summary", ""),
            })
        return tool_result(
            {"symbol": symbol, "articles": articles, "count": len(articles)},
            "yfinance", "get_press_releases", {"symbol": symbol, "limit": limit},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_press_releases",
                          {"symbol": symbol})


if __name__ == "__main__":
    mcp.run()
