"""MCP Server: SEC EDGAR — company filings, XBRL facts (read-only).

Run standalone:  python mcp_servers/sec_edgar_server.py
"""

import os
from mcp.server.fastmcp import FastMCP
from mcp_servers._shared import load_project_env, http_get, tool_result, tool_error, RateLimiter

load_project_env()

mcp = FastMCP(
    "mcp_filings_sec_edgar",
    instructions="Read-only SEC EDGAR data: company filings, XBRL facts, ticker-to-CIK mapping",
)

_UA = os.getenv("SEC_EDGAR_USER_AGENT",
                "InvestmentIntelligenceStudio/1.0 (admin@example.com)")
_HEADERS = {"User-Agent": _UA, "Accept": "application/json"}
_RL = RateLimiter(600)


@mcp.tool()
def get_company_filings(cik: str) -> str:
    """Get recent filings for a company by CIK number.

    Args:
        cik: SEC Central Index Key (will be zero-padded to 10 digits)
    """
    try:
        cik_padded = cik.zfill(10)
        _RL.wait()
        data = http_get(f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
                        headers=_HEADERS)
        return tool_result(data, "sec_edgar", "get_company_filings", {"cik": cik_padded})
    except Exception as e:
        return tool_error(str(e), "sec_edgar", "get_company_filings", {"cik": cik})


@mcp.tool()
def get_company_facts(cik: str) -> str:
    """Get XBRL financial facts for a company (revenue, net income, etc.)."""
    try:
        cik_padded = cik.zfill(10)
        _RL.wait()
        data = http_get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json",
            headers=_HEADERS)
        return tool_result(data, "sec_edgar", "get_company_facts", {"cik": cik_padded})
    except Exception as e:
        return tool_error(str(e), "sec_edgar", "get_company_facts", {"cik": cik})


@mcp.tool()
def ticker_to_cik(ticker: str) -> str:
    """Resolve a stock ticker to its SEC CIK number."""
    try:
        _RL.wait()
        data = http_get("https://www.sec.gov/files/company_tickers.json",
                        headers=_HEADERS)
        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                return tool_result(
                    {"cik": str(entry["cik_str"]), "ticker": entry["ticker"],
                     "title": entry.get("title", "")},
                    "sec_edgar", "ticker_to_cik", {"ticker": ticker})
        return tool_error(f"Ticker {ticker} not found", "sec_edgar",
                          "ticker_to_cik", {"ticker": ticker})
    except Exception as e:
        return tool_error(str(e), "sec_edgar", "ticker_to_cik", {"ticker": ticker})


if __name__ == "__main__":
    mcp.run()
