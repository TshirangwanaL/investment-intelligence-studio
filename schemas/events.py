"""News, earnings, and catalyst event schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsEvent(BaseModel):
    event_id: str = ""
    title: str = ""
    url: str = ""
    source: str = ""
    published_at: datetime = Field(default_factory=datetime.utcnow)
    tickers: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    sentiment_score: float = 0.0
    tone: str = "neutral"
    summary: str = ""
    gdelt_doc_id: str = ""
    relevance_score: float = 0.0


class TranscriptInsight(BaseModel):
    ticker: str
    fiscal_period: str = ""
    call_date: str = ""
    guidance_signals: list[str] = Field(default_factory=list)
    tone_shift: str = "neutral"
    tone_confidence: float = 0.5
    risk_mentions: list[str] = Field(default_factory=list)
    kpi_highlights: list[dict] = Field(default_factory=list)
    key_quotes: list[str] = Field(default_factory=list)
    summary: str = ""
    source: str = "FMP"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class EarningsCalendarItem(BaseModel):
    ticker: str
    date: str
    fiscal_period: str = ""
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    source: str = "FMP"


class CatalystEvent(BaseModel):
    event_id: str = ""
    ticker: str = ""
    event_type: str = ""
    date: str = ""
    description: str = ""
    significance: str = "medium"
    source: str = ""
