"""DuckDB persistence adapter for Daily Execution Ledger."""
from datetime import date, datetime, timezone
from pathlib import Path
import threading
from typing import Optional

import duckdb

from decision.daily_execution import DailyExecutionLedgerState, DailyExecutionRecord
from decision.daily_repository import (
    DailyExecutionConflictError,
    DailyExecutionRepository,
    DailyExecutionRepositoryError,
)


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _to_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DuckDbDailyExecutionRepository:
    """Thread-safe DuckDB implementation of DailyExecutionRepository protocol."""

    def __init__(
        self,
        db_path: str = "data/database/decisions.duckdb",
        conn: Optional[duckdb.DuckDBPyConnection] = None,
    ) -> None:
        self._lock = threading.Lock()

        if conn is not None:
            self._conn = conn
        else:
            p = Path(db_path)
            if str(db_path) != ":memory:":
                p.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(db_path))

        self.initialize_schema()

    def initialize_schema(self) -> None:
        """Idempotently creates table schema for daily_decision_executions."""
        with self._lock:
            try:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_decision_executions (
                        run_date DATE PRIMARY KEY,
                        status VARCHAR NOT NULL,
                        decision_id VARCHAR NOT NULL,
                        timezone_name VARCHAR NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        lease_expires_at TIMESTAMP,
                        attempt_count INTEGER NOT NULL,
                        error_message VARCHAR
                    );
                    """
                )
            except Exception as err:
                raise DailyExecutionRepositoryError("Failed to initialize daily executions schema") from err

    def reserve(self, record: DailyExecutionRecord) -> None:
        if not isinstance(record, DailyExecutionRecord):
            raise TypeError("record must be DailyExecutionRecord")

        start_naive = _to_naive_utc(record.started_at)
        lease_naive = _to_naive_utc(record.lease_expires_at)

        with self._lock:
            try:
                # Primary key constraint check / insertion
                self._conn.execute("BEGIN TRANSACTION;")
                self._conn.execute(
                    """
                    INSERT INTO daily_decision_executions (
                        run_date,
                        status,
                        decision_id,
                        timezone_name,
                        started_at,
                        completed_at,
                        lease_expires_at,
                        attempt_count,
                        error_message
                    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, NULL);
                    """,
                    [
                        record.run_date,
                        record.status.value,
                        record.decision_id,
                        record.timezone_name,
                        start_naive,
                        lease_naive,
                        record.attempt_count,
                    ],
                )
                self._conn.execute("COMMIT;")
            except duckdb.ConstraintException as err:
                self._rollback_safe()
                raise DailyExecutionConflictError(
                    f"Execution record for run_date '{record.run_date}' already exists."
                ) from err
            except Exception as err:
                self._rollback_safe()
                raise DailyExecutionRepositoryError("Failed to reserve daily execution") from err

    def get_by_run_date(self, run_date: date) -> Optional[DailyExecutionRecord]:
        if not isinstance(run_date, date):
            raise TypeError("run_date must be a date instance")

        with self._lock:
            try:
                cursor = self._conn.execute(
                    """
                    SELECT run_date, status, decision_id, timezone_name, started_at, completed_at, lease_expires_at, attempt_count, error_message
                    FROM daily_decision_executions
                    WHERE run_date = ?;
                    """,
                    [run_date],
                )
                row = cursor.fetchone()
                if row is None:
                    return None

                return self._parse_row(row)
            except Exception as err:
                raise DailyExecutionRepositoryError("Failed to query get_by_run_date") from err

    def mark_completed(self, run_date: date, decision_id: str, completed_at: datetime) -> DailyExecutionRecord:
        comp_naive = _to_naive_utc(completed_at)
        with self._lock:
            try:
                self._conn.execute("BEGIN TRANSACTION;")
                self._conn.execute(
                    """
                    UPDATE daily_decision_executions
                    SET status = ?, completed_at = ?, lease_expires_at = NULL, error_message = NULL
                    WHERE run_date = ? AND decision_id = ?;
                    """,
                    [DailyExecutionLedgerState.COMPLETED.value, comp_naive, run_date, decision_id],
                )
                self._conn.execute("COMMIT;")

                rec = self.get_by_run_date(run_date)
                if rec is None:
                    raise DailyExecutionRepositoryError("Record missing after completion update")
                return rec
            except Exception as err:
                self._rollback_safe()
                raise DailyExecutionRepositoryError("Failed to mark execution completed") from err

    def mark_failed(self, run_date: date, error_message: str, completed_at: datetime) -> DailyExecutionRecord:
        comp_naive = _to_naive_utc(completed_at)
        with self._lock:
            try:
                self._conn.execute("BEGIN TRANSACTION;")
                self._conn.execute(
                    """
                    UPDATE daily_decision_executions
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE run_date = ?;
                    """,
                    [DailyExecutionLedgerState.FAILED.value, comp_naive, error_message, run_date],
                )
                self._conn.execute("COMMIT;")

                rec = self.get_by_run_date(run_date)
                if rec is None:
                    raise DailyExecutionRepositoryError("Record missing after failure update")
                return rec
            except Exception as err:
                self._rollback_safe()
                raise DailyExecutionRepositoryError("Failed to mark execution failed") from err

    def takeover_retry(
        self,
        run_date: date,
        decision_id: str,
        new_started_at: datetime,
        new_lease_expires_at: datetime,
    ) -> DailyExecutionRecord:
        start_naive = _to_naive_utc(new_started_at)
        lease_naive = _to_naive_utc(new_lease_expires_at)

        with self._lock:
            try:
                self._conn.execute("BEGIN TRANSACTION;")
                self._conn.execute(
                    """
                    UPDATE daily_decision_executions
                    SET status = ?,
                        decision_id = ?,
                        started_at = ?,
                        completed_at = NULL,
                        lease_expires_at = ?,
                        attempt_count = attempt_count + 1,
                        error_message = NULL
                    WHERE run_date = ?;
                    """,
                    [
                        DailyExecutionLedgerState.RUNNING.value,
                        decision_id,
                        start_naive,
                        lease_naive,
                        run_date,
                    ],
                )
                self._conn.execute("COMMIT;")

                rec = self.get_by_run_date(run_date)
                if rec is None:
                    raise DailyExecutionRepositoryError("Record missing after takeover retry")
                return rec
            except Exception as err:
                self._rollback_safe()
                raise DailyExecutionRepositoryError("Failed to take over execution retry") from err

    def _parse_row(self, row: tuple) -> DailyExecutionRecord:
        (
            col_date,
            col_status,
            col_dec_id,
            col_tz,
            col_started_at,
            col_completed_at,
            col_lease_at,
            col_attempt,
            col_error,
        ) = row

        r_date = col_date if isinstance(col_date, date) else datetime.strptime(str(col_date), "%Y-%m-%d").date()

        return DailyExecutionRecord(
            run_date=r_date,
            status=DailyExecutionLedgerState(col_status),
            decision_id=col_dec_id,
            timezone_name=col_tz,
            started_at=_to_aware_utc(col_started_at if isinstance(col_started_at, datetime) else datetime.fromisoformat(str(col_started_at))),
            completed_at=_to_aware_utc(col_completed_at if col_completed_at is None or isinstance(col_completed_at, datetime) else datetime.fromisoformat(str(col_completed_at))),
            lease_expires_at=_to_aware_utc(col_lease_at if col_lease_at is None or isinstance(col_lease_at, datetime) else datetime.fromisoformat(str(col_lease_at))),
            attempt_count=int(col_attempt),
            error_message=col_error,
        )

    def _rollback_safe(self) -> None:
        try:
            self._conn.execute("ROLLBACK;")
        except Exception:
            pass
