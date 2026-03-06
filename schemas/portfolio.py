"""Portfolio, trade, and factor schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Position(BaseModel):
    ticker: str
    weight: float = 0.0
    shares: float = 0.0
    avg_cost: float = 0.0
    current_price: float = 0.0
    sector: str = ""


class PortfolioState(BaseModel):
    version: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    name: str = "default"
    positions: list[Position] = Field(default_factory=list)
    cash_weight: float = 1.0
    total_value: float = 100_000.0
    notes: str = ""

    @property
    def tickers(self) -> list[str]:
        return [p.ticker for p in self.positions]

    @property
    def weight_map(self) -> dict[str, float]:
        return {p.ticker: p.weight for p in self.positions}


class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REBALANCE = "rebalance"


class TradeAction(BaseModel):
    ticker: str
    action: ActionType
    current_weight: float = 0.0
    target_weight: float = 0.0
    weight_delta: float = 0.0
    rationale: str = ""
    confidence: float = 0.5
    is_new_position: bool = False
    is_full_exit: bool = False
    news_risk_flags: list[str] = Field(default_factory=list)


class BucketType(str, Enum):
    AUTO = "auto"
    REVIEW = "review"


class TradePlan(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actions: list[TradeAction] = Field(default_factory=list)
    total_turnover: float = 0.0
    portfolio_before: Optional[PortfolioState] = None
    portfolio_after: Optional[PortfolioState] = None
    auto_actions: list[TradeAction] = Field(default_factory=list)
    review_actions: list[TradeAction] = Field(default_factory=list)
    rationale_summary: str = ""
    agent_source: str = ""


class FactorExposure(BaseModel):
    """Fama-French factor regression results."""

    ticker_or_portfolio: str = "portfolio"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_type: str = "FF3"
    alpha: float = 0.0
    alpha_pvalue: float = 1.0
    betas: dict[str, float] = Field(default_factory=dict)
    beta_pvalues: dict[str, float] = Field(default_factory=dict)
    r_squared: float = 0.0
    adj_r_squared: float = 0.0
    observations: int = 0
    interpretation: str = ""


class PortfolioRiskMetrics(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    annual_vol: float = 0.0
    daily_var_95: float = 0.0
    max_drawdown_proxy: float = 0.0
    sharpe_proxy: float = 0.0
    top5_concentration: float = 0.0
    hhi: float = 0.0
    correlation_avg: float = 0.0
    sector_weights: dict[str, float] = Field(default_factory=dict)
