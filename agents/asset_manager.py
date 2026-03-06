"""Asset Manager Agent — portfolio construction, rebalancing, constraints."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from schemas.portfolio import TradePlan, TradeAction, ActionType


class AssetManagerAgent(BaseAgent):
    AGENT_NAME = "asset_manager"
    ALLOWED_TOOLS = {
        "mcp_quant",
        "mcp_marketdata_alpha_vantage",
        "mcp_news_gdelt",
        "mcp_macro_fred",
    }
    SYSTEM_PROMPT = """You are an institutional portfolio manager.
Given current portfolio, risk assessment, equity theses, and market context:
- Propose weight adjustments with rationale
- Respect investment policy constraints
- Compute turnover
- Flag high-conviction vs. marginal changes
- Challenge the equity analyst when appropriate
Output a structured trade plan as JSON. Never exceed policy limits."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        portfolio = context.get("portfolio", {})
        risk_assessment = context.get("risk_assessment", {})
        equity_theses = context.get("equity_theses", {})
        market_context = context.get("market_context", {})
        policy = context.get("policy", {})
        challenge_request = context.get("challenge_request", "")

        challenge_section = ""
        if challenge_request:
            challenge_section = f"\n\nCHALLENGE FROM PM: {challenge_request}"

        prompt = f"""Propose portfolio adjustments based on the following:

CURRENT PORTFOLIO:
{json.dumps(portfolio, indent=2, default=str)[:2000]}

RISK ASSESSMENT:
{json.dumps(risk_assessment, indent=2, default=str)[:1500]}

EQUITY THESES:
{json.dumps(equity_theses, indent=2, default=str)[:2000]}

MARKET CONTEXT:
{json.dumps(market_context, indent=2, default=str)[:1000]}

POLICY CONSTRAINTS:
{json.dumps(policy, indent=2, default=str)[:1000]}
{challenge_section}

Return valid JSON:
{{
  "actions": [
    {{
      "ticker": "...",
      "action": "buy|sell|hold|rebalance",
      "current_weight": 0.0,
      "target_weight": 0.0,
      "weight_delta": 0.0,
      "rationale": "...",
      "confidence": 0.0,
      "is_new_position": false,
      "is_full_exit": false,
      "news_risk_flags": []
    }}
  ],
  "total_turnover": 0.0,
  "rationale_summary": "..."
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
                "actions": [],
                "total_turnover": 0.0,
                "rationale_summary": raw[:500],
            }

        actions = []
        for a in parsed.get("actions", []):
            actions.append(TradeAction(
                ticker=a.get("ticker", ""),
                action=ActionType(a.get("action", "hold")),
                current_weight=a.get("current_weight", 0.0),
                target_weight=a.get("target_weight", 0.0),
                weight_delta=a.get("weight_delta", 0.0),
                rationale=a.get("rationale", ""),
                confidence=a.get("confidence", 0.5),
                is_new_position=a.get("is_new_position", False),
                is_full_exit=a.get("is_full_exit", False),
                news_risk_flags=a.get("news_risk_flags", []),
            ))

        plan = TradePlan(
            actions=actions,
            total_turnover=parsed.get("total_turnover", 0.0),
            rationale_summary=parsed.get("rationale_summary", ""),
            agent_source=self.AGENT_NAME,
        )

        output = plan.model_dump(mode="json")
        self._log_output(output)
        return output
