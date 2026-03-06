"""Decision Synthesizer Agent — final decision note from all agent outputs.

This agent has NO tool access — it only reads prior agent outputs.
"""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent


class DecisionSynthesizerAgent(BaseAgent):
    AGENT_NAME = "decision_synthesizer"
    ALLOWED_TOOLS: set[str] = set()
    SYSTEM_PROMPT = """You are the decision synthesizer for an institutional investment committee.
You receive outputs from: Market Narrative, Equity Analyst, Risk Analytics, and Asset Manager agents.
Your role:
1. Produce a final decision note
2. State key assumptions explicitly
3. Assign a confidence level (0-1)
4. State "what changes my mind" — conditions that would invalidate this decision
5. Provide a clear vote: buy, hold, or sell with reasoning

You have NO tool access. You work only from the agent outputs provided.
Be concise, structured, and suitable for an investment committee memo."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        market_narrative = context.get("market_narrative", {})
        equity_thesis = context.get("equity_thesis", {})
        risk_assessment = context.get("risk_assessment", {})
        trade_plan = context.get("trade_plan", {})
        debate_log = context.get("debate_log", [])

        debate_section = ""
        if debate_log:
            debate_section = f"\n\nDEBATE TRANSCRIPT:\n{json.dumps(debate_log, indent=2, default=str)[:2000]}"

        prompt = f"""Synthesize the following agent outputs into a final investment committee decision note.

MARKET NARRATIVE:
{json.dumps(market_narrative, indent=2, default=str)[:1500]}

EQUITY THESIS:
{json.dumps(equity_thesis, indent=2, default=str)[:2000]}

RISK ASSESSMENT:
{json.dumps(risk_assessment, indent=2, default=str)[:1500]}

TRADE PLAN:
{json.dumps(trade_plan, indent=2, default=str)[:1500]}
{debate_section}

Return valid JSON:
{{
  "decision_note": "...",
  "key_assumptions": ["..."],
  "confidence": 0.0,
  "vote": "buy|hold|sell",
  "vote_rationale": "...",
  "what_changes_my_mind": ["..."],
  "dissenting_views": ["..."],
  "recommended_review_date": "YYYY-MM-DD"
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
                "decision_note": raw[:500],
                "key_assumptions": [],
                "confidence": 0.3,
                "vote": "hold",
                "vote_rationale": "Unable to parse synthesis",
                "what_changes_my_mind": [],
                "dissenting_views": [],
            }

        parsed["agent"] = self.AGENT_NAME
        self._log_output(parsed)
        return parsed
