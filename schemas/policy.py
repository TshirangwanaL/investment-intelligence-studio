"""Governance policy and constraints schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ConstraintRule(BaseModel):
    rule_id: str
    name: str
    description: str = ""
    enabled: bool = True
    parameter: str = ""
    threshold: float = 0.0
    severity: Severity = Severity.WARNING


class ConstraintAlert(BaseModel):
    rule: ConstraintRule
    current_value: float = 0.0
    message: str = ""
    triggered_at: datetime = Field(default_factory=datetime.utcnow)


class AutopilotThresholds(BaseModel):
    max_weight_delta_auto: float = 0.015
    max_turnover_auto: float = 0.05
    min_confidence_auto: float = 0.70
    allow_new_positions_auto: bool = False
    allow_full_exits_auto: bool = False
    high_risk_news_categories: list[str] = Field(
        default_factory=lambda: [
            "litigation", "fraud", "bankruptcy", "major_regulatory"
        ]
    )
    event_lockout_enabled: bool = False
    event_lockout_days: int = 2


class Policy(BaseModel):
    policy_id: str = "default"
    name: str = "Default Investment Policy"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    max_position_weight: float = 0.10
    top5_max_concentration: float = 0.50
    sector_cap: float = 0.30
    cash_floor: float = 0.02
    max_turnover_per_rebalance: float = 0.15
    min_positions: int = 5
    max_positions: int = 50
    constraints: list[ConstraintRule] = Field(default_factory=list)
    autopilot: AutopilotThresholds = Field(default_factory=AutopilotThresholds)
