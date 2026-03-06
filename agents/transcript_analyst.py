"""Transcript Analyst — LLM-powered earnings call intelligence.

Fills the gap: FMP pulls transcripts but nobody reads them.
This agent extracts structured insights: guidance signals, tone shifts,
risk mentions, KPI highlights, and key quotes.
"""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from schemas.events import TranscriptInsight


class TranscriptAnalystAgent(BaseAgent):
    AGENT_NAME = "transcript_analyst"
    ALLOWED_TOOLS = {"mcp_events_fmp"}
    SYSTEM_PROMPT = """You are a senior buy-side analyst specialising in earnings call analysis.
Given an earnings call transcript, extract structured intelligence.

Focus on:
1. **Guidance signals** — forward-looking statements (raised, lowered, maintained, vague)
2. **Tone shift** — compare management tone to previous calls (more cautious, more confident, defensive, evasive)
3. **Risk mentions** — specific risks management called out (supply chain, competition, regulatory, macro)
4. **KPI highlights** — key metrics management emphasized with their values
5. **Key quotes** — the 3-5 most material verbatim quotes

Return valid JSON with NO commentary outside the JSON object."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        ticker = context.get("ticker", "AAPL")
        year = context.get("year", 2025)
        quarter = context.get("quarter", 4)

        transcript_text = ""
        if "mcp_events_fmp" in self._tools:
            fmp = self._get_tool("mcp_events_fmp")
            result = fmp.get_earnings_transcript(
                symbol=ticker, year=year, quarter=quarter
            )
            if result.success and result.data:
                items = result.data if isinstance(result.data, list) else [result.data]
                for item in items:
                    transcript_text += item.get("content", str(item))[:12000]

        if not transcript_text.strip():
            return TranscriptInsight(
                ticker=ticker,
                fiscal_period=f"Q{quarter} {year}",
                summary="No transcript available for this period.",
            ).model_dump(mode="json")

        prompt = f"""Analyze this earnings call transcript for {ticker} (Q{quarter} {year}).

TRANSCRIPT (truncated):
{transcript_text[:10000]}

Return valid JSON:
{{
  "guidance_signals": ["signal1", "signal2"],
  "tone_shift": "more_confident|more_cautious|defensive|evasive|neutral|optimistic",
  "tone_confidence": 0.0-1.0,
  "risk_mentions": ["risk1", "risk2"],
  "kpi_highlights": [{{"metric": "...", "value": "...", "context": "..."}}],
  "key_quotes": ["quote1", "quote2"],
  "summary": "2-3 sentence summary of the call's most material points"
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
                "guidance_signals": [],
                "tone_shift": "neutral",
                "tone_confidence": 0.3,
                "risk_mentions": [],
                "kpi_highlights": [],
                "key_quotes": [],
                "summary": raw[:500],
            }

        insight = TranscriptInsight(
            ticker=ticker,
            fiscal_period=f"Q{quarter} {year}",
            guidance_signals=parsed.get("guidance_signals", []),
            tone_shift=parsed.get("tone_shift", "neutral"),
            tone_confidence=parsed.get("tone_confidence", 0.5),
            risk_mentions=parsed.get("risk_mentions", []),
            kpi_highlights=parsed.get("kpi_highlights", []),
            key_quotes=parsed.get("key_quotes", []),
            summary=parsed.get("summary", ""),
        )

        output = insight.model_dump(mode="json")
        self._log_output(output, ticker=ticker)
        return output
