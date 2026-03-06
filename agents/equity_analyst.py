"""Equity Analyst Agent — single-stock deep dive with thesis generation."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from schemas.thesis import EquityThesis, ThesisClaim, ThesisDirection


class EquityAnalystAgent(BaseAgent):
    AGENT_NAME = "equity_analyst"
    ALLOWED_TOOLS = {
        "mcp_marketdata_alpha_vantage",
        "mcp_events_fmp",
        "mcp_filings_sec_edgar",
        "mcp_news_gdelt",
    }
    SYSTEM_PROMPT = """You are a senior equity research analyst at an institutional fund.
For a given ticker, produce a structured thesis covering:
- Bull case and bear case
- Key catalysts (positive and negative)
- Key risks
- Valuation signal (cheap/fair/expensive — coarse, rule-based)
- Scenario outputs under stress conditions
- Confidence level (0-1)
Output valid JSON. Cite data sources. Do NOT produce buy/sell recommendations — 
only analysis."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        ticker = context.get("ticker", "AAPL")
        scenario_request = context.get("scenario_request", "")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        price_data: dict = {}
        overview_data: dict = {}
        earnings_data: dict = {}
        transcript_data: dict = {}
        filings_data: dict = {}
        news_data: dict = {}

        def _fetch_prices():
            if "mcp_marketdata_alpha_vantage" not in self._tools:
                return
            av = self._get_tool("mcp_marketdata_alpha_vantage")
            nonlocal price_data, overview_data
            price_data = av.get_daily(symbol=ticker).to_dict()
            overview_data = av.get_overview(symbol=ticker).to_dict()

        def _fetch_earnings():
            if "mcp_events_fmp" not in self._tools:
                return
            fmp = self._get_tool("mcp_events_fmp")
            nonlocal earnings_data, transcript_data
            earnings_data = fmp.get_earnings_calendar_for_ticker(symbol=ticker).to_dict()
            try:
                tr_result = fmp.get_earnings_transcript(symbol=ticker, year=2025, quarter=4)
                if tr_result.success and tr_result.data:
                    items = tr_result.data if isinstance(tr_result.data, list) else [tr_result.data]
                    transcript_data = {"content": items[0].get("content", "")[:4000]}
            except Exception:
                pass

        def _fetch_filings():
            if "mcp_filings_sec_edgar" not in self._tools:
                return
            edgar = self._get_tool("mcp_filings_sec_edgar")
            nonlocal filings_data
            cik_result = edgar.get_ticker_to_cik(ticker=ticker)
            if cik_result.success and "cik" in (cik_result.data or {}):
                filings_data = edgar.get_company_filings(cik=cik_result.data["cik"]).to_dict()

        def _fetch_news():
            if "mcp_news_gdelt" not in self._tools:
                return
            gdelt = self._get_tool("mcp_news_gdelt")
            nonlocal news_data
            news_data = gdelt.search_news(query=ticker, max_records=10).to_dict()

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(_fetch_prices),
                pool.submit(_fetch_earnings),
                pool.submit(_fetch_filings),
                pool.submit(_fetch_news),
            ]
            for f in as_completed(futures):
                try:
                    f.result(timeout=30)
                except Exception:
                    pass

        scenario_section = ""
        if scenario_request:
            scenario_section = f"\n\nADDITIONAL SCENARIO REQUEST: {scenario_request}"

        def _compact(d: dict, limit: int = 1200) -> str:
            return json.dumps(d, separators=(",", ":"), default=str)[:limit]

        prompt = f"""Produce a structured equity thesis for {ticker}.

IMPORTANT: Be concise. summary ≤3 sentences, bull_case ≤3 sentences, bear_case ≤3 sentences. Each catalyst/risk is a single short string. Keep total response under 2000 tokens.

PRICE DATA:
{_compact(price_data.get('data', {}), 1200)}

COMPANY OVERVIEW:
{_compact(overview_data.get('data', {}), 1200)}

EARNINGS:
{_compact(earnings_data.get('data', {}), 800)}

SEC FILINGS:
{_compact(filings_data.get('data', {}), 800)}

NEWS:
{_compact(news_data.get('data', {}), 800)}

TRANSCRIPT:
{_compact(transcript_data, 1500)}
{scenario_section}

Return ONLY valid JSON (no markdown fences). All string values must be plain strings, not objects.
{{
  "ticker": "{ticker}",
  "direction": "bull|bear|neutral",
  "summary": "2-3 sentence summary",
  "bull_case": "2-3 sentence bull case",
  "bear_case": "2-3 sentence bear case",
  "catalysts": ["short string 1", "short string 2", "short string 3"],
  "risks": ["short string 1", "short string 2", "short string 3"],
  "valuation_signal": "cheap|fair|expensive",
  "scenarios": [{{"name": "scenario name", "impact": "-20", "probability": 0.25}}],
  "claims": [{{"text": "claim text", "direction": "bull|bear|neutral", "category": "fundamentals", "confidence": 0.7}}],
  "confidence": 0.0
}}"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = self._call_llm(messages, max_tokens=4096)

        def _extract_json(text: str) -> dict | None:
            """Try multiple strategies to extract valid JSON from LLM output."""
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()
            try:
                return json.loads(clean)
            except json.JSONDecodeError:
                pass
            import re
            m = re.search(r'\{.*\}', clean, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
            truncated = clean
            for _ in range(20):
                truncated = truncated.rsplit(",", 1)[0]
                for closing in ["}", "]}}", "]}}}", "]}]}}"]:
                    try:
                        return json.loads(truncated + closing)
                    except json.JSONDecodeError:
                        continue
            return None

        parsed = _extract_json(raw)
        if parsed is None:
            parsed = {
                "ticker": ticker,
                "direction": "neutral",
                "summary": "Thesis generation produced incomplete output. Please try again.",
                "bull_case": "",
                "bear_case": "",
                "catalysts": [],
                "risks": [],
                "valuation_signal": "fair",
                "scenarios": [],
                "claims": [],
                "confidence": 0.3,
            }

        def _to_str_list(items: list) -> list[str]:
            """LLMs sometimes return dicts instead of strings for catalysts/risks."""
            result = []
            for item in items:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    text = item.get("description") or item.get("text") or item.get("name", "")
                    prefix = item.get("type", "")
                    if prefix and text:
                        result.append(f"[{prefix}] {text}")
                    elif text:
                        result.append(text)
                    else:
                        result.append(str(item))
                else:
                    result.append(str(item))
            return result

        def _to_claims(items: list) -> list[ThesisClaim]:
            claims = []
            for c in items:
                if isinstance(c, dict):
                    if "text" not in c and "description" in c:
                        c["text"] = c.pop("description")
                    if "text" not in c and "claim" in c:
                        c["text"] = c.pop("claim")
                    if "text" not in c:
                        c["text"] = str(c)
                    dir_val = c.get("direction", "neutral")
                    if dir_val not in ("bull", "bear", "neutral"):
                        dir_val = "neutral"
                    c["direction"] = dir_val
                    try:
                        claims.append(ThesisClaim(**c))
                    except Exception:
                        claims.append(ThesisClaim(text=str(c)))
                elif isinstance(c, str):
                    claims.append(ThesisClaim(text=c))
            return claims

        direction_raw = parsed.get("direction", "neutral")
        if direction_raw not in ("bull", "bear", "neutral"):
            direction_raw = "neutral"

        confidence_raw = parsed.get("confidence", 0.5)
        try:
            confidence_val = float(confidence_raw)
            if confidence_val > 1:
                confidence_val = confidence_val / 100
        except (ValueError, TypeError):
            confidence_val = 0.5

        thesis = EquityThesis(
            ticker=parsed.get("ticker", ticker),
            direction=ThesisDirection(direction_raw),
            summary=parsed.get("summary", ""),
            bull_case=parsed.get("bull_case", ""),
            bear_case=parsed.get("bear_case", ""),
            catalysts=_to_str_list(parsed.get("catalysts", [])),
            risks=_to_str_list(parsed.get("risks", [])),
            valuation_signal=parsed.get("valuation_signal", "fair"),
            scenarios=parsed.get("scenarios", []),
            claims=_to_claims(parsed.get("claims", [])),
            confidence=confidence_val,
            agent_source=self.AGENT_NAME,
        )

        output = thesis.model_dump(mode="json")
        self._log_output(output, ticker=ticker)
        return output
