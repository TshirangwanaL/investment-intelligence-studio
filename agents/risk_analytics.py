"""Risk Analytics Agent — portfolio risk assessment and scenario impacts."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from schemas.portfolio import PortfolioState, PortfolioRiskMetrics


class RiskAnalyticsAgent(BaseAgent):
    AGENT_NAME = "risk_analytics"
    ALLOWED_TOOLS = {
        "mcp_quant",
        "mcp_marketdata_alpha_vantage",
        "mcp_macro_fred",
    }
    SYSTEM_PROMPT = """You are an institutional risk analyst. Given portfolio positions
and market data, assess:
- Portfolio volatility (annualized proxy)
- Correlation structure
- Concentration risk (HHI + top-5)
- Drawdown proxy
- Scenario impacts (market crash, rates shock, sector shock)
Be quantitative and precise. Cite methodology. Flag any data limitations."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        portfolio_data = context.get("portfolio", {})
        market_context = context.get("market_context", {})

        weights = []
        tickers = []
        if isinstance(portfolio_data, dict) and "positions" in portfolio_data:
            for p in portfolio_data["positions"]:
                tickers.append(p.get("ticker", ""))
                weights.append(p.get("weight", 0.0))

        quant_results = {}
        if "mcp_quant" in self._tools and weights:
            quant = self._get_tool("mcp_quant")

            conc_result = quant.concentration_hhi(weights=weights)
            quant_results["concentration"] = conc_result.to_dict()

        price_data = {}
        if "mcp_marketdata_alpha_vantage" in self._tools and tickers:
            av = self._get_tool("mcp_marketdata_alpha_vantage")
            for t in tickers[:10]:
                result = av.get_daily(symbol=t, outputsize="compact")
                if result.success:
                    price_data[t] = result.to_dict()

        prompt = f"""Assess the risk profile for this portfolio:

TICKERS & WEIGHTS:
{json.dumps(dict(zip(tickers, weights)), indent=2)}

QUANT METRICS:
{json.dumps(quant_results, indent=2, default=str)[:2000]}

MARKET CONTEXT:
{json.dumps(market_context, indent=2, default=str)[:1000]}

Return valid JSON:
{{
  "annual_vol_estimate": 0.0,
  "concentration_assessment": "...",
  "top_risks": ["..."],
  "scenario_impacts": {{
    "market_crash": {{"impact_pct": -0.0, "description": "..."}},
    "rates_shock": {{"impact_pct": -0.0, "description": "..."}},
    "sector_concentration": {{"impact_pct": -0.0, "description": "..."}}
  }},
  "recommendations": ["..."],
  "data_limitations": ["..."]
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
                "annual_vol_estimate": 0.0,
                "concentration_assessment": "Unable to parse",
                "top_risks": [],
                "scenario_impacts": {},
                "recommendations": [],
                "data_limitations": ["LLM parse error"],
                "raw_response": raw[:500],
            }

        parsed["agent"] = self.AGENT_NAME
        parsed["tickers"] = tickers
        parsed["weights"] = weights
        self._log_output(parsed)
        return parsed
