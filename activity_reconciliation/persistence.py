"""Append-only DuckDB persistence for immutable reconciliation results."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import threading

import duckdb

from activity_reconciliation.models import (
    ActivityExecutionOutcome, ActivityReference, MatchStatus,
    ReconciliationItem, ReconciliationResult, ReplacementEvidence,
)


class ReconciliationConflictError(RuntimeError):
    pass


class ReconciliationResultCodec:
    SCHEMA_VERSION = "1.0"

    def encode(self, result: ReconciliationResult) -> str:
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "reconciliation_id": result.reconciliation_id,
            "input_fingerprint": result.input_fingerprint,
            "policy_version": result.policy_version,
            "target_local_date": result.target_local_date.isoformat(),
            "timezone_name": result.timezone_name,
            "plan_id": result.plan_id,
            "plan_version": result.plan_version,
            "finalized": result.finalized,
            "planned_session_ids": list(result.planned_session_ids),
            "activity_event_ids": list(result.activity_event_ids),
            "items": [{
                "match_status": item.match_status.value,
                "planned_session_id": item.planned_session_id,
                "activity": None if item.activity is None else item.activity.__dict__,
                "candidate_session_ids": list(item.candidate_session_ids),
                "candidate_activity_event_ids": list(item.candidate_activity_event_ids),
                "execution_outcome": None if item.execution_outcome is None else item.execution_outcome.value,
                "completion_percent": item.completion_percent,
                "reason_codes": list(item.reason_codes),
                "warning_codes": list(item.warning_codes),
            } for item in result.items],
            "replacement_evidence": [item.__dict__ for item in result.replacement_evidence],
            "evaluated_at": result.evaluated_at.isoformat(),
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def decode(self, payload: str) -> ReconciliationResult:
        data = json.loads(payload)
        if data["schema_version"] != self.SCHEMA_VERSION:
            raise ValueError("unsupported reconciliation schema version")
        return ReconciliationResult(
            reconciliation_id=data["reconciliation_id"],
            input_fingerprint=data["input_fingerprint"],
            policy_version=data["policy_version"],
            target_local_date=date.fromisoformat(data["target_local_date"]),
            timezone_name=data["timezone_name"], plan_id=data["plan_id"],
            plan_version=data["plan_version"], finalized=data["finalized"],
            planned_session_ids=tuple(data["planned_session_ids"]),
            activity_event_ids=tuple(data["activity_event_ids"]),
            items=tuple(ReconciliationItem(
                match_status=MatchStatus(item["match_status"]),
                planned_session_id=item["planned_session_id"],
                activity=None if item["activity"] is None else ActivityReference(**item["activity"]),
                candidate_session_ids=tuple(item["candidate_session_ids"]),
                candidate_activity_event_ids=tuple(item["candidate_activity_event_ids"]),
                execution_outcome=None if item["execution_outcome"] is None else ActivityExecutionOutcome(item["execution_outcome"]),
                completion_percent=item["completion_percent"],
                reason_codes=tuple(item["reason_codes"]), warning_codes=tuple(item["warning_codes"]),
            ) for item in data["items"]),
            replacement_evidence=tuple(ReplacementEvidence(**item) for item in data["replacement_evidence"]),
            evaluated_at=datetime.fromisoformat(data["evaluated_at"]),
        )


class DuckDbReconciliationResultRepository:
    """Stores each deterministic input snapshot once; changed inputs append rows."""

    def __init__(self, db_path) -> None:
        self._db_path = str(db_path)
        self._codec = ReconciliationResultCodec()
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self):
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(self._db_path)

    def _ensure_schema(self):
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS activity_reconciliation_results (
                        reconciliation_id VARCHAR PRIMARY KEY,
                        input_fingerprint VARCHAR UNIQUE NOT NULL,
                        target_local_date DATE NOT NULL,
                        plan_id VARCHAR NOT NULL,
                        plan_version INTEGER NOT NULL,
                        finalized BOOLEAN NOT NULL,
                        policy_version VARCHAR NOT NULL,
                        evaluated_at_utc TIMESTAMP NOT NULL,
                        record_schema_version VARCHAR NOT NULL,
                        payload_json VARCHAR NOT NULL
                    )
                """)
            finally:
                connection.close()

    def save(self, result: ReconciliationResult) -> bool:
        payload = self._codec.encode(result)
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT payload_json FROM activity_reconciliation_results WHERE input_fingerprint = ?",
                    [result.input_fingerprint],
                ).fetchone()
                if row is not None:
                    return False
                evaluated = result.evaluated_at
                if evaluated.tzinfo is not None:
                    evaluated = evaluated.astimezone(timezone.utc).replace(tzinfo=None)
                connection.execute(
                    "INSERT INTO activity_reconciliation_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [result.reconciliation_id, result.input_fingerprint,
                     result.target_local_date, result.plan_id, result.plan_version,
                     result.finalized, result.policy_version, evaluated,
                     self._codec.SCHEMA_VERSION, payload],
                )
                return True
            finally:
                connection.close()

    def get_by_fingerprint(self, fingerprint: str) -> ReconciliationResult | None:
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT payload_json FROM activity_reconciliation_results WHERE input_fingerprint = ?",
                    [fingerprint],
                ).fetchone()
                return None if row is None else self._codec.decode(row[0])
            finally:
                connection.close()

    def get_by_id(self, reconciliation_id: str) -> ReconciliationResult | None:
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT payload_json FROM activity_reconciliation_results WHERE reconciliation_id = ?",
                    [reconciliation_id],
                ).fetchone()
                return None if row is None else self._codec.decode(row[0])
            finally:
                connection.close()

    def get_latest_for_date(self, target_local_date: date) -> ReconciliationResult | None:
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    """SELECT payload_json FROM activity_reconciliation_results
                       WHERE target_local_date = ?
                       ORDER BY evaluated_at_utc DESC, reconciliation_id DESC
                       LIMIT 1""",
                    [target_local_date],
                ).fetchone()
                return None if row is None else self._codec.decode(row[0])
            finally:
                connection.close()

    def list_for_date(self, target_date: date) -> tuple[ReconciliationResult, ...]:
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT payload_json FROM activity_reconciliation_results WHERE target_local_date = ? ORDER BY evaluated_at_utc, reconciliation_id",
                    [target_date],
                ).fetchall()
                return tuple(self._codec.decode(row[0]) for row in rows)
            finally:
                connection.close()
