"""Audit trail and tool-call logging schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    AGENT_OUTPUT = "agent_output"
    TOOL_CALL = "tool_call"
    TRADE_PROPOSED = "trade_proposed"
    TRADE_AUTO_APPLIED = "trade_auto_applied"
    TRADE_APPROVED = "trade_approved"
    TRADE_REJECTED = "trade_rejected"
    PORTFOLIO_COMMITTED = "portfolio_committed"
    THESIS_CREATED = "thesis_created"
    THESIS_DRIFT = "thesis_drift"
    CONSTRAINT_ALERT = "constraint_alert"
    PM_NOTE = "pm_note"
    KILL_SWITCH = "kill_switch"
    POLICY_CHANGE = "policy_change"


class ToolCallRecord(BaseModel):
    call_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    server_name: str = ""
    tool_name: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    response_summary: str = ""
    latency_ms: float = 0.0
    success: bool = True
    error_message: str = ""
    cached: bool = False


class AuditLogEntry(BaseModel):
    entry_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: AuditAction
    agent_name: str = ""
    ticker: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    pm_rationale: str = ""
    portfolio_version_before: Optional[int] = None
    portfolio_version_after: Optional[int] = None
    data_snapshot_key: str = ""
