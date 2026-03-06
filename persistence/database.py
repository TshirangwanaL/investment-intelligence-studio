"""SQLite database layer — versioned portfolio states, decisions, tool logs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

from config import DB_PATH

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS portfolio_states (
    version INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'default',
    data_json TEXT NOT NULL,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    agent_name TEXT DEFAULT '',
    ticker TEXT DEFAULT '',
    details_json TEXT DEFAULT '{}',
    pm_rationale TEXT DEFAULT '',
    portfolio_version_before INTEGER,
    portfolio_version_after INTEGER,
    data_snapshot_key TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tool_call_logs (
    call_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    server_name TEXT DEFAULT '',
    tool_name TEXT DEFAULT '',
    parameters_json TEXT DEFAULT '{}',
    response_summary TEXT DEFAULT '',
    latency_ms REAL DEFAULT 0,
    success INTEGER DEFAULT 1,
    error_message TEXT DEFAULT '',
    cached INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS theses (
    thesis_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drift_checks (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    thesis_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence TEXT DEFAULT '',
    data_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    data_json TEXT NOT NULL
);
"""


class Database:
    _instance: Optional[Database] = None

    def __new__(cls) -> Database:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA_SQL)

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_portfolio(self, data_json: str, name: str = "default", notes: str = "") -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO portfolio_states (timestamp, name, data_json, notes) VALUES (?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), name, data_json, notes),
            )
            return cur.lastrowid  # type: ignore

    def get_latest_portfolio(self, name: str = "default") -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM portfolio_states WHERE name = ? ORDER BY version DESC LIMIT 1",
                (name,),
            ).fetchone()
            if row:
                return {"version": row["version"], **json.loads(row["data_json"])}
        return None

    def get_portfolio_history(self, name: str = "default", limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_states WHERE name = ? ORDER BY version DESC LIMIT ?",
                (name, limit),
            ).fetchall()
            return [
                {"version": r["version"], "timestamp": r["timestamp"],
                 "notes": r["notes"], **json.loads(r["data_json"])}
                for r in rows
            ]

    def log_decision(self, entry: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO decisions
                   (decision_id, timestamp, action, agent_name, ticker,
                    details_json, pm_rationale, portfolio_version_before,
                    portfolio_version_after, data_snapshot_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.get("entry_id", ""),
                    entry.get("timestamp", datetime.utcnow().isoformat()),
                    entry.get("action", ""),
                    entry.get("agent_name", ""),
                    entry.get("ticker", ""),
                    json.dumps(entry.get("details", {}), default=str),
                    entry.get("pm_rationale", ""),
                    entry.get("portfolio_version_before"),
                    entry.get("portfolio_version_after"),
                    entry.get("data_snapshot_key", ""),
                ),
            )

    def get_decisions(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def log_tool_call(self, record: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO tool_call_logs
                   (call_id, timestamp, server_name, tool_name,
                    parameters_json, response_summary, latency_ms,
                    success, error_message, cached)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.get("call_id", ""),
                    record.get("timestamp", datetime.utcnow().isoformat()),
                    record.get("server_name", ""),
                    record.get("tool_name", ""),
                    json.dumps(record.get("parameters", {}), default=str),
                    record.get("response_summary", ""),
                    record.get("latency_ms", 0),
                    int(record.get("success", True)),
                    record.get("error_message", ""),
                    int(record.get("cached", False)),
                ),
            )

    def get_tool_calls(self, limit: int = 200) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tool_call_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def save_thesis(self, thesis_id: str, ticker: str, data_json: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO theses (thesis_id, ticker, timestamp, data_json) VALUES (?, ?, ?, ?)",
                (thesis_id, ticker, datetime.utcnow().isoformat(), data_json),
            )

    def get_theses(self, ticker: Optional[str] = None, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            if ticker:
                rows = conn.execute(
                    "SELECT * FROM theses WHERE ticker = ? ORDER BY timestamp DESC LIMIT ?",
                    (ticker, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM theses ORDER BY timestamp DESC LIMIT ?", (limit,)
                ).fetchall()
            return [
                {"thesis_id": r["thesis_id"], "ticker": r["ticker"],
                 "timestamp": r["timestamp"], **json.loads(r["data_json"])}
                for r in rows
            ]

    def save_drift_check(self, thesis_id: str, claim_id: str, status: str,
                         evidence: str, data_json: str = "{}") -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO drift_checks
                   (thesis_id, claim_id, timestamp, status, evidence, data_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (thesis_id, claim_id, datetime.utcnow().isoformat(), status, evidence, data_json),
            )

    def get_drift_checks(self, thesis_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            if thesis_id:
                rows = conn.execute(
                    "SELECT * FROM drift_checks WHERE thesis_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (thesis_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM drift_checks ORDER BY timestamp DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    def save_policy(self, policy_id: str, data_json: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO policies (policy_id, timestamp, data_json) VALUES (?, ?, ?)",
                (policy_id, datetime.utcnow().isoformat(), data_json),
            )

    def get_policy(self, policy_id: str = "default") -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM policies WHERE policy_id = ?", (policy_id,)
            ).fetchone()
            if row:
                return json.loads(row["data_json"])
        return None
