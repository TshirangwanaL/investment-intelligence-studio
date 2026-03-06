"""Market-data and macro schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OHLCBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


class TechnicalIndicator(BaseModel):
    name: str
    date: str
    value: float
    metadata: dict = Field(default_factory=dict)


class MarketContext(BaseModel):
    """Snapshot of current market conditions produced by the Market Narrative Agent."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    regime_label: str = "unknown"
    regime_confidence: float = 0.0
    macro_drivers: list[str] = Field(default_factory=list)
    sector_themes: list[str] = Field(default_factory=list)
    risk_sentiment: str = "neutral"
    summary: str = ""
    data_sources: list[str] = Field(default_factory=list)


class MacroSeries(BaseModel):
    series_id: str
    description: str
    observations: list[dict] = Field(default_factory=list)
    units: str = ""
    frequency: str = ""
    source: str = "FRED"
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class MacroRegime(BaseModel):
    label: str
    drivers: list[str] = Field(default_factory=list)
    uncertainty: float = 0.5
    classification_method: str = "rule_based"
    indicators: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
