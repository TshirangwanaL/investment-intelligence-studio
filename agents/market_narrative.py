"""Market Narrative Agent — regime, macro drivers, sector themes."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from schemas.market import MarketContext


class MarketNarrativeAgent(BaseAgent):
    AGENT_NAME = "market_narrative"
    ALLOWED_TOOLS = {
        "mcp_news_gdelt",
        "mcp_macro_fred",
        "mcp_marketdata_alpha_vantage",
    }
    SYSTEM_PROMPT = """You are an institutional market narrative analyst.
Your role: synthesize macro data, news flow, and market technicals into a
concise market regime assessment. Output structured JSON with:
- regime_label: one of [risk_on, risk_off, transition, uncertain]
- regime_confidence: 0-1
- macro_drivers: list of key drivers
- sector_themes: list of active themes
- risk_sentiment: [bullish, neutral, bearish]
- summary: 2-3 sentence narrative
Be precise and cite data points. Do NOT make trading recommendations."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        macro_data = {}
        news_data = {}
        market_data = {}

        if "mcp_macro_fred" in self._tools:
            fred = self._get_tool("mcp_macro_fred")
            macro_result = fred.get_macro_dashboard()
            macro_data = macro_result.to_dict()

        if "mcp_news_gdelt" in self._tools:
            gdelt = self._get_tool("mcp_news_gdelt")
            news_result = gdelt.search_news(
                query="market economy financial",
                max_records=20,
                timespan="7d",
            )
            news_data = news_result.to_dict()

        if "mcp_marketdata_alpha_vantage" in self._tools:
            av = self._get_tool("mcp_marketdata_alpha_vantage")
            spy_result = av.get_quote(symbol="SPY")
            market_data = spy_result.to_dict()

        prompt = f"""Analyze the current market environment using the following data:

MACRO DATA:
{json.dumps(macro_data.get('data', {}), indent=2, default=str)[:3000]}

NEWS FLOW:
{json.dumps(news_data.get('data', {}), indent=2, default=str)[:2000]}

MARKET DATA:
{json.dumps(market_data.get('data', {}), indent=2, default=str)[:1000]}

Return valid JSON matching this schema:
{{
  "regime_label": "risk_on|risk_off|transition|uncertain",
  "regime_confidence": 0.0-1.0,
  "macro_drivers": ["driver1", "driver2"],
  "sector_themes": ["theme1", "theme2"],
  "risk_sentiment": "bullish|neutral|bearish",
  "summary": "narrative text"
}}"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = self._call_llm(messages)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "regime_label": "uncertain",
                "regime_confidence": 0.3,
                "macro_drivers": ["data_parse_error"],
                "sector_themes": [],
                "risk_sentiment": "neutral",
                "summary": raw[:500],
            }

        parsed["data_sources"] = ["FRED", "GDELT", "Alpha Vantage"]
        result = MarketContext(**parsed)
        output = result.model_dump(mode="json")
        self._log_output(output)
        return output
