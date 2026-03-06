"""Equity thesis and drift-detection schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ThesisDirection(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"


class ThesisClaim(BaseModel):
    claim_id: str = ""
    text: str
    direction: ThesisDirection = ThesisDirection.NEUTRAL
    category: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DriftStatus(str, Enum):
    NO_CHANGE = "no_change"
    WEAKENED = "weakened"
    INVALIDATED = "invalidated"
    STRENGTHENED = "strengthened"


class DriftCheckResult(BaseModel):
    claim_id: str
    original_text: str
    status: DriftStatus = DriftStatus.NO_CHANGE
    evidence: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = 0.5


class EquityThesis(BaseModel):
    thesis_id: str = ""
    ticker: str
    direction: ThesisDirection = ThesisDirection.NEUTRAL
    summary: str = ""
    bull_case: str = ""
    bear_case: str = ""
    catalysts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    valuation_signal: str = ""
    scenarios: list[dict] = Field(default_factory=list)
    claims: list[ThesisClaim] = Field(default_factory=list)
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    agent_source: str = "equity_analyst"
    data_snapshot_keys: list[str] = Field(default_factory=list)
    drift_checks: list[DriftCheckResult] = Field(default_factory=list)
