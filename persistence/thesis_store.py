"""Thesis persistence — store, retrieve, track drift."""

from __future__ import annotations

import json
import uuid
from typing import Optional

from schemas.thesis import EquityThesis, DriftCheckResult
from persistence.database import Database


class ThesisStore:
    def __init__(self) -> None:
        self.db = Database()

    def save(self, thesis: EquityThesis) -> str:
        if not thesis.thesis_id:
            thesis.thesis_id = str(uuid.uuid4())
        for i, claim in enumerate(thesis.claims):
            if not claim.claim_id:
                claim.claim_id = f"{thesis.thesis_id}_c{i}"
        self.db.save_thesis(
            thesis.thesis_id,
            thesis.ticker,
            thesis.model_dump_json(),
        )
        return thesis.thesis_id

    def get(self, thesis_id: str) -> Optional[EquityThesis]:
        rows = self.db.get_theses()
        for row in rows:
            if row.get("thesis_id") == thesis_id:
                return EquityThesis.model_validate(row)
        return None

    def get_by_ticker(self, ticker: str) -> list[EquityThesis]:
        rows = self.db.get_theses(ticker=ticker)
        return [EquityThesis.model_validate(r) for r in rows]

    def get_all(self, limit: int = 50) -> list[EquityThesis]:
        rows = self.db.get_theses(limit=limit)
        return [EquityThesis.model_validate(r) for r in rows]

    def record_drift(self, result: DriftCheckResult) -> None:
        self.db.save_drift_check(
            thesis_id=result.claim_id.split("_c")[0] if "_c" in result.claim_id else result.claim_id,
            claim_id=result.claim_id,
            status=result.status.value,
            evidence=result.evidence,
            data_json=result.model_dump_json(),
        )

    def get_drift_history(self, thesis_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        return self.db.get_drift_checks(thesis_id=thesis_id, limit=limit)
