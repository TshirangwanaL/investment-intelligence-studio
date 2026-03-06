"""MCP Server: FRED — Federal Reserve Economic Data (read-only).

Run standalone:  python mcp_servers/fred_server.py
"""

import os
from mcp.server.fastmcp import FastMCP
from mcp_servers._shared import load_project_env, http_get, tool_result, tool_error, RateLimiter

load_project_env()

mcp = FastMCP(
    "mcp_macro_fred",
    instructions="Read-only macro/economic data from FRED: CPI, rates, unemployment, yield spreads",
)

_KEY = os.getenv("FRED_API_KEY", "")
_BASE = "https://api.stlouisfed.org/fred"
_RL = RateLimiter(120)

MACRO_SERIES = {
    "CPI": "CPIAUCSL", "CORE_CPI": "CPILFESL", "FED_FUNDS": "FEDFUNDS",
    "UNEMPLOYMENT": "UNRATE", "GDP": "GDP", "T10Y2Y": "T10Y2Y",
    "T10Y3M": "T10Y3M", "BAA_SPREAD": "BAAFFM", "VIX": "VIXCLS",
    "M2": "M2SL", "INITIAL_CLAIMS": "ICSA",
}


def _fred(**kw) -> dict:
    _RL.wait()
    return http_get(f"{_BASE}/series/observations",
                    params={**kw, "api_key": _KEY, "file_type": "json"})


@mcp.tool()
def get_series_observations(series_id: str, limit: int = 500,
                            observation_start: str = "",
                            observation_end: str = "") -> str:
    """Get observations for a FRED series (e.g. FEDFUNDS, CPIAUCSL, UNRATE).

    Args:
        series_id: FRED series identifier
        limit: Max observations to return
        observation_start: Start date (YYYY-MM-DD)
        observation_end: End date (YYYY-MM-DD)
    """
    try:
        params: dict = {"series_id": series_id, "limit": limit, "sort_order": "desc"}
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        _RL.wait()
        data = http_get(f"{_BASE}/series/observations",
                        params={**params, "api_key": _KEY, "file_type": "json"})
        return tool_result(data, "fred", "get_series_observations",
                           {"series_id": series_id, "limit": limit})
    except Exception as e:
        return tool_error(str(e), "fred", "get_series_observations",
                          {"series_id": series_id})


@mcp.tool()
def get_series_info(series_id: str) -> str:
    """Get metadata about a FRED series (description, units, frequency)."""
    try:
        _RL.wait()
        data = http_get(f"{_BASE}/series",
                        params={"series_id": series_id, "api_key": _KEY, "file_type": "json"})
        return tool_result(data, "fred", "get_series_info", {"series_id": series_id})
    except Exception as e:
        return tool_error(str(e), "fred", "get_series_info", {"series_id": series_id})


@mcp.tool()
def search_series(search_text: str, limit: int = 20) -> str:
    """Search for FRED series by keyword."""
    try:
        _RL.wait()
        data = http_get(f"{_BASE}/series/search",
                        params={"search_text": search_text, "limit": limit,
                                "api_key": _KEY, "file_type": "json"})
        return tool_result(data, "fred", "search_series",
                           {"search_text": search_text, "limit": limit})
    except Exception as e:
        return tool_error(str(e), "fred", "search_series", {"search_text": search_text})


@mcp.tool()
def get_macro_dashboard() -> str:
    """Fetch a curated set of macro indicators for regime analysis.

    Returns latest values for: CPI, Fed Funds, Unemployment, GDP, yield spreads, VIX, etc.
    """
    try:
        results = {}
        for label, sid in MACRO_SERIES.items():
            try:
                _RL.wait()
                resp = http_get(f"{_BASE}/series/observations",
                                params={"series_id": sid, "limit": 12,
                                        "sort_order": "desc",
                                        "api_key": _KEY, "file_type": "json"})
                obs = resp.get("observations", [])
                results[label] = {"series_id": sid, "latest": obs[0] if obs else None,
                                  "recent": obs[:6]}
            except Exception as exc:
                results[label] = {"series_id": sid, "error": str(exc)}
        return tool_result(results, "fred", "get_macro_dashboard", {"dashboard": True})
    except Exception as e:
        return tool_error(str(e), "fred", "get_macro_dashboard", {})


if __name__ == "__main__":
    mcp.run()
