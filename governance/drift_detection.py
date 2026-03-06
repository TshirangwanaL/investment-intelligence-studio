"""Thesis Drift Detection — re-check claims against new data/news."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from config import settings
from schemas.thesis import DriftCheckResult, DriftStatus, EquityThesis, ThesisClaim
from persistence.thesis_store import ThesisStore


class DriftDetector:
    def __init__(self) -> None:
        self.store = ThesisStore()

    def check_claim(
        self,
        claim: ThesisClaim,
        current_news: list[dict] | None = None,
        current_price_data: dict | None = None,
        current_macro: dict | None = None,
    ) -> DriftCheckResult:
        """Evaluate a single thesis claim against current data."""
        evidence_parts: list[str] = []
        evidence_sources: list[str] = []

        if current_news:
            contradicting = []
            for article in current_news:
                title = article.get("title", "").lower()
                claim_keywords = claim.text.lower().split()[:5]
                if any(kw in title for kw in claim_keywords):
                    contradicting.append(article.get("title", ""))
                    evidence_sources.append(article.get("url", ""))
            if contradicting:
                evidence_parts.append(f"Related news: {'; '.join(contradicting[:3])}")

        try:
            if settings.use_azure:
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                )
                model_name = settings.AZURE_OPENAI_DEPLOYMENT
            else:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                model_name = settings.LLM_MODEL

            context = {
                "claim": claim.text,
                "direction": claim.direction.value,
                "news_headlines": [n.get("title", "") for n in (current_news or [])[:10]],
                "price_data_summary": str(current_price_data)[:500] if current_price_data else "N/A",
                "macro_summary": str(current_macro)[:500] if current_macro else "N/A",
            }

            llm_kwargs: dict = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": (
                        "You evaluate whether an investment thesis claim still holds. "
                        "Return JSON: {\"status\": \"no_change|weakened|invalidated|strengthened\", "
                        "\"evidence\": \"brief explanation\", \"confidence\": 0.0-1.0}"
                    )},
                    {"role": "user", "content": json.dumps(context)},
                ],
            }
            if not model_name.startswith("o"):
                llm_kwargs["temperature"] = 0.1
            resp = client.chat.completions.create(**llm_kwargs)
            raw = resp.choices[0].message.content or "{}"
            parsed = json.loads(raw)
            status = DriftStatus(parsed.get("status", "no_change"))
            evidence_parts.append(parsed.get("evidence", ""))
            confidence = parsed.get("confidence", 0.5)
        except Exception:
            status = DriftStatus.NO_CHANGE
            confidence = 0.3
            evidence_parts.append("LLM unavailable — defaulting to no_change")

        return DriftCheckResult(
            claim_id=claim.claim_id,
            original_text=claim.text,
            status=status,
            evidence=" | ".join(evidence_parts),
            evidence_sources=evidence_sources,
            checked_at=datetime.utcnow(),
            confidence=confidence,
        )

    def check_thesis(
        self,
        thesis: EquityThesis,
        current_news: list[dict] | None = None,
        current_price_data: dict | None = None,
        current_macro: dict | None = None,
    ) -> list[DriftCheckResult]:
        results: list[DriftCheckResult] = []
        for claim in thesis.claims:
            result = self.check_claim(
                claim, current_news, current_price_data, current_macro
            )
            results.append(result)
            self.store.record_drift(result)
        return results

    def get_drift_summary(self, thesis_id: str) -> dict[str, Any]:
        history = self.store.get_drift_history(thesis_id=thesis_id)
        summary = {
            "thesis_id": thesis_id,
            "total_checks": len(history),
            "invalidated": sum(1 for h in history if h.get("status") == "invalidated"),
            "weakened": sum(1 for h in history if h.get("status") == "weakened"),
            "strengthened": sum(1 for h in history if h.get("status") == "strengthened"),
            "no_change": sum(1 for h in history if h.get("status") == "no_change"),
            "latest_checks": history[:10],
        }
        return summary
