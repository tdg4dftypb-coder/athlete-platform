"""Append-only DuckDB persistence for operational runtime audit revisions."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import threading
from typing import Union

import duckdb

from production_runtime.models import ProductionDailyRuntimeResult, RuntimeStatus
from production_runtime.persistence.codec import RuntimeAuditCodec
from production_runtime.repository import (
    RuntimeAuditConflictError,
    RuntimeAuditDataError,
    RuntimeAuditRepositoryError,
)


def _naive_utc(value: datetime | None) -> datetime | None:
    return None if value is None else value.astimezone(timezone.utc).replace(tzinfo=None)


class DuckDbRuntimeAuditRepository:
    """Stores every lifecycle revision; never overwrites an attempt snapshot."""

    def __init__(self, db_path: Union[str, Path], *, read_only: bool = False) -> None:
        self._db_path = str(db_path)
        self._read_only = read_only
        self._lock = threading.Lock()
        self._codec = RuntimeAuditCodec()
        if self._read_only:
            if self._db_path == ":memory:" or not Path(self._db_path).is_file():
                raise RuntimeAuditRepositoryError(
                    f"Runtime audit database is unavailable at '{self._db_path}'"
                )
        else:
            self._ensure_schema()

    def _connection(self) -> duckdb.DuckDBPyConnection:
        try:
            if self._db_path != ":memory:" and not self._read_only:
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            return duckdb.connect(self._db_path, read_only=self._read_only)
        except Exception as error:
            raise RuntimeAuditRepositoryError(
                f"Failed to connect to runtime audit database at '{self._db_path}'"
            ) from error

    def _ensure_schema(self) -> None:
        with self._lock:
            connection = self._connection()
            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS production_runtime_audit_revisions (
                        runtime_id VARCHAR NOT NULL,
                        revision INTEGER NOT NULL,
                        logical_execution_key VARCHAR NOT NULL,
                        contract_version VARCHAR NOT NULL,
                        target_local_date DATE NOT NULL,
                        timezone_name VARCHAR NOT NULL,
                        status VARCHAR NOT NULL,
                        started_at_utc TIMESTAMP NOT NULL,
                        completed_at_utc TIMESTAMP,
                        record_schema_version VARCHAR NOT NULL,
                        payload_json VARCHAR NOT NULL,
                        PRIMARY KEY (runtime_id, revision)
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS production_runtime_audit_target_date_idx
                    ON production_runtime_audit_revisions (target_local_date, started_at_utc, runtime_id)
                    """
                )
            except Exception as error:
                raise RuntimeAuditRepositoryError("Failed to initialize runtime audit schema") from error
            finally:
                connection.close()

    def append(
        self,
        result: ProductionDailyRuntimeResult,
        expected_revision: int | None = None,
    ) -> None:
        if not isinstance(result, ProductionDailyRuntimeResult):
            raise TypeError("result must be ProductionDailyRuntimeResult")
        if self._read_only:
            raise RuntimeAuditRepositoryError("Runtime audit repository is read-only")
        if expected_revision is not None and (
            not isinstance(expected_revision, int) or expected_revision < 1
        ):
            raise ValueError("expected_revision must be an int >= 1 or None")

        payload = self._codec.encode(result)
        with self._lock:
            connection = self._connection()
            try:
                connection.execute("BEGIN TRANSACTION")
                same_revision = connection.execute(
                    """SELECT payload_json FROM production_runtime_audit_revisions
                       WHERE runtime_id = ? AND revision = ?""",
                    [result.runtime_id, result.revision],
                ).fetchone()
                if same_revision is not None:
                    if same_revision[0] == payload:
                        connection.execute("ROLLBACK")
                        return
                    raise RuntimeAuditConflictError(
                        f"Runtime '{result.runtime_id}' revision {result.revision} already exists with different payload"
                    )

                latest_row = connection.execute(
                    """SELECT revision, payload_json FROM production_runtime_audit_revisions
                       WHERE runtime_id = ? ORDER BY revision DESC LIMIT 1""",
                    [result.runtime_id],
                ).fetchone()

                if latest_row is None:
                    if expected_revision is not None or result.revision != 1:
                        raise RuntimeAuditConflictError("Initial runtime audit must be revision 1 without expected_revision")
                else:
                    latest_revision, latest_payload = latest_row
                    if expected_revision != latest_revision or result.revision != latest_revision + 1:
                        raise RuntimeAuditConflictError(
                            f"Runtime '{result.runtime_id}' revision conflict; latest is {latest_revision}"
                        )
                    previous = self._codec.decode(latest_payload)
                    self._validate_transition(previous, result)

                connection.execute(
                    """
                    INSERT INTO production_runtime_audit_revisions (
                        runtime_id, revision, logical_execution_key, contract_version,
                        target_local_date, timezone_name, status, started_at_utc,
                        completed_at_utc, record_schema_version, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        result.runtime_id,
                        result.revision,
                        result.logical_execution_key,
                        result.contract_version,
                        result.target_local_date,
                        result.timezone_name,
                        result.status.value,
                        _naive_utc(result.started_at_utc),
                        _naive_utc(result.completed_at_utc),
                        self._codec.SCHEMA_VERSION,
                        payload,
                    ],
                )
                connection.execute("COMMIT")
            except (RuntimeAuditConflictError, RuntimeAuditDataError):
                try:
                    connection.execute("ROLLBACK")
                except Exception:
                    pass
                raise
            except duckdb.ConstraintException as error:
                try:
                    connection.execute("ROLLBACK")
                except Exception:
                    pass
                raise RuntimeAuditConflictError("Runtime audit append conflicted") from error
            except Exception as error:
                try:
                    connection.execute("ROLLBACK")
                except Exception:
                    pass
                raise RuntimeAuditRepositoryError("Failed to append runtime audit revision") from error
            finally:
                connection.close()

    @staticmethod
    def _validate_transition(
        previous: ProductionDailyRuntimeResult,
        current: ProductionDailyRuntimeResult,
    ) -> None:
        identity_fields = (
            "runtime_id",
            "logical_execution_key",
            "contract_version",
            "target_local_date",
            "timezone_name",
            "started_at_utc",
        )
        if any(getattr(previous, name) != getattr(current, name) for name in identity_fields):
            raise RuntimeAuditConflictError("Runtime attempt identity fields are immutable")
        if previous.status is not RuntimeStatus.RUNNING:
            raise RuntimeAuditConflictError("Terminal runtime audit cannot transition")
        previous_phases = {item.phase: item for item in previous.phases}
        current_phases = {item.phase: item for item in current.phases}
        if any(current_phases.get(phase) != value for phase, value in previous_phases.items()):
            raise RuntimeAuditConflictError("Persisted phase results are immutable")

    def get_by_runtime_id(self, runtime_id: str) -> ProductionDailyRuntimeResult | None:
        if not isinstance(runtime_id, str) or not runtime_id.strip():
            raise ValueError("runtime_id must be a non-empty string")
        with self._lock:
            connection = self._connection()
            try:
                row = connection.execute(
                    """SELECT payload_json FROM production_runtime_audit_revisions
                       WHERE runtime_id = ? ORDER BY revision DESC LIMIT 1""",
                    [runtime_id],
                ).fetchone()
                return None if row is None else self._codec.decode(row[0])
            except RuntimeAuditDataError:
                raise
            except Exception as error:
                raise RuntimeAuditRepositoryError("Failed to read runtime audit") from error
            finally:
                connection.close()

    def list_for_target_date(self, target_date: date) -> tuple[ProductionDailyRuntimeResult, ...]:
        if type(target_date) is not date:
            raise TypeError("target_date must be a date")
        with self._lock:
            connection = self._connection()
            try:
                rows = connection.execute(
                    """
                    SELECT payload_json FROM production_runtime_audit_revisions AS audit
                    WHERE target_local_date = ?
                      AND revision = (
                          SELECT MAX(revision) FROM production_runtime_audit_revisions
                          WHERE runtime_id = audit.runtime_id
                      )
                    ORDER BY started_at_utc ASC, runtime_id ASC
                    """,
                    [target_date],
                ).fetchall()
                return tuple(self._codec.decode(row[0]) for row in rows)
            except RuntimeAuditDataError:
                raise
            except Exception as error:
                raise RuntimeAuditRepositoryError("Failed to list runtime attempts for target date") from error
            finally:
                connection.close()

    def get_latest(self) -> ProductionDailyRuntimeResult | None:
        with self._lock:
            connection = self._connection()
            try:
                row = connection.execute(
                    """
                    SELECT payload_json FROM production_runtime_audit_revisions AS audit
                    WHERE revision = (
                        SELECT MAX(revision) FROM production_runtime_audit_revisions
                        WHERE runtime_id = audit.runtime_id
                    )
                    ORDER BY started_at_utc DESC, runtime_id DESC
                    LIMIT 1
                    """
                ).fetchone()
                return None if row is None else self._codec.decode(row[0])
            except RuntimeAuditDataError:
                raise
            except Exception as error:
                raise RuntimeAuditRepositoryError("Failed to read latest runtime attempt") from error
            finally:
                connection.close()
