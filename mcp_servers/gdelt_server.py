"""MCP Server: News — article search and sentiment signals (read-only).

Powered by yfinance news (no API key, no rate limits).
Run standalone:  python mcp_servers/gdelt_server.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import yfinance as yf
from mcp.server.fastmcp import FastMCP
from mcp_servers._shared import load_project_env, tool_result, tool_error

load_project_env()

mcp = FastMCP(
    "mcp_news_gdelt",
    instructions="Read-only news data: article search by ticker, recent headlines",
)


def _parse_yf_news(raw_news: list, max_records: int = 50) -> list[dict]:
    """Normalise yfinance news items into a flat article list."""
    articles = []
    for item in raw_news[:max_records]:
        content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
        pub = content.get("provider", {})
        pub_name = pub.get("displayName", "") if isinstance(pub, dict) else str(pub)

        thumb = content.get("thumbnail")
        thumb_url = ""
        if isinstance(thumb, dict):
            resolutions = thumb.get("resolutions", [])
            if resolutions:
                thumb_url = resolutions[-1].get("url", "")

        articles.append({
            "title": content.get("title") or item.get("title", "Untitled"),
            "url": content.get("canonicalUrl", {}).get("url", "") or item.get("link", ""),
            "domain": pub_name,
            "seendate": content.get("pubDate", "") or item.get("published", ""),
            "tone": 0,
            "language": content.get("locale", "en-US"),
            "summary": content.get("summary", ""),
            "thumbnail": thumb_url,
        })
    return articles


@mcp.tool()
def search_news(query: str, mode: str = "ArtList",
                max_records: int = 50, timespan: str = "7d") -> str:
    """Search for news articles related to a query (ticker or keywords).

    Args:
        query: Search keywords or ticker (e.g. 'AAPL', 'inflation recession')
        mode: Kept for compatibility — always returns article list
        max_records: Max articles to return (1-100)
        timespan: Kept for compatibility — yfinance returns recent news
    """
    try:
        tickers = [t.strip().upper() for t in query.replace(",", " ").split() if t.strip()]
        if not tickers:
            tickers = [query.strip().upper()]

        all_articles: list[dict] = []
        for sym in tickers[:5]:
            try:
                ticker = yf.Ticker(sym.replace(".", "-"))
                raw = ticker.news or []
                arts = _parse_yf_news(raw, max_records=max_records)
                for a in arts:
                    a["_ticker"] = sym
                all_articles.extend(arts)
            except Exception:
                continue

        all_articles = all_articles[:max_records]

        return tool_result(
            {"articles": all_articles, "count": len(all_articles),
             "source": "yfinance"},
            "yfinance", "search_news",
            {"query": query, "mode": mode, "max_records": max_records,
             "timespan": timespan},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "search_news", {"query": query})


@mcp.tool()
def get_tone_timeline(query: str, timespan: str = "30d") -> str:
    """Get a simplified sentiment proxy using recent price momentum.

    Note: True tone timelines require a dedicated news API.
    This returns price-based momentum as a sentiment proxy.
    """
    try:
        ticker = yf.Ticker(query.strip().upper().replace(".", "-"))
        hist = ticker.history(period="1mo", interval="1d")
        if hist.empty:
            return tool_result({"timeline": [], "note": "No data"},
                               "yfinance", "get_tone_timeline", {"query": query})
        timeline = []
        for dt, row in hist.iterrows():
            o, c = float(row.get("Open", 0)), float(row.get("Close", 0))
            daily_return = ((c - o) / o * 100) if o else 0
            timeline.append({
                "date": dt.strftime("%Y-%m-%d"),
                "tone": round(daily_return, 2),
            })
        return tool_result(
            {"timeline": timeline, "note": "Price-based sentiment proxy"},
            "yfinance", "get_tone_timeline",
            {"query": query, "timespan": timespan},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_tone_timeline", {"query": query})


@mcp.tool()
def get_volume_timeline(query: str, timespan: str = "30d") -> str:
    """Get news/trading volume timeline for a query."""
    try:
        ticker = yf.Ticker(query.strip().upper().replace(".", "-"))
        hist = ticker.history(period="1mo", interval="1d")
        if hist.empty:
            return tool_result({"timeline": []}, "yfinance",
                               "get_volume_timeline", {"query": query})
        avg_vol = float(hist["Volume"].mean()) if not hist["Volume"].empty else 1
        timeline = []
        for dt, row in hist.iterrows():
            vol = int(row.get("Volume", 0))
            timeline.append({
                "date": dt.strftime("%Y-%m-%d"),
                "volume": vol,
                "relative": round(vol / avg_vol, 2) if avg_vol else 1,
            })
        return tool_result(
            {"timeline": timeline},
            "yfinance", "get_volume_timeline",
            {"query": query, "timespan": timespan},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_volume_timeline", {"query": query})


@mcp.tool()
def get_theme_news(theme: str, max_records: int = 30) -> str:
    """Get news for a market theme by searching major index tickers.

    Args:
        theme: Theme keyword (e.g. 'inflation', 'AI', 'energy')
        max_records: Max articles
    """
    try:
        _THEME_TICKERS = {
            "inflation": ["TIP", "GLD", "SHY"],
            "recession": ["SPY", "TLT", "VIX"],
            "ai": ["NVDA", "MSFT", "GOOGL"],
            "energy": ["XOM", "CVX", "XLE"],
            "crypto": ["BTC-USD", "ETH-USD", "COIN"],
            "tech": ["QQQ", "AAPL", "MSFT"],
            "rates": ["TLT", "SHY", "AGG"],
        }
        tickers = _THEME_TICKERS.get(theme.lower(), ["SPY", "QQQ"])

        all_articles: list[dict] = []
        for sym in tickers:
            try:
                ticker = yf.Ticker(sym)
                raw = ticker.news or []
                arts = _parse_yf_news(raw, max_records=10)
                for a in arts:
                    a["_theme"] = theme
                all_articles.extend(arts)
            except Exception:
                continue

        return tool_result(
            {"articles": all_articles[:max_records], "theme": theme,
             "count": len(all_articles[:max_records])},
            "yfinance", "get_theme_news",
            {"theme": theme, "max_records": max_records},
        )
    except Exception as e:
        return tool_error(str(e), "yfinance", "get_theme_news", {"theme": theme})


if __name__ == "__main__":
    mcp.run()
