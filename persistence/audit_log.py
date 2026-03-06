"""High-level audit logger wrapping the database layer."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from schemas.audit import AuditAction, AuditLogEntry, ToolCallRecord
from persistence.database import Database


class AuditLogger:
    def __init__(self) -> None:
        self.db = Database()

    def log(
        self,
        action: AuditAction,
        agent_name: str = "",
        ticker: str = "",
        details: dict[str, Any] | None = None,
        pm_rationale: str = "",
        tool_calls: list[ToolCallRecord] | None = None,
        portfolio_version_before: int | None = None,
        portfolio_version_after: int | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            action=action,
            agent_name=agent_name,
            ticker=ticker,
            details=details or {},
            pm_rationale=pm_rationale,
            tool_calls=tool_calls or [],
            portfolio_version_before=portfolio_version_before,
            portfolio_version_after=portfolio_version_after,
        )
        self.db.log_decision(entry.model_dump(mode="json"))

        for tc in entry.tool_calls:
            self.db.log_tool_call(tc.model_dump(mode="json"))

        return entry

    def get_timeline(self, limit: int = 100) -> list[dict]:
        return self.db.get_decisions(limit=limit)

    def get_tool_call_history(self, limit: int = 200) -> list[dict]:
        return self.db.get_tool_calls(limit=limit)
