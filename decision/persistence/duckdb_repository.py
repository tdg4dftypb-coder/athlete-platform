from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Optional

import duckdb

from decision.history_v2 import DecisionAuditRecord
from decision.persistence.record_codec import DecisionAuditRecordCodec
from decision.repository import (
    DecisionAuditRecordConflictError,
    DecisionAuditRecordDataError,
    DecisionAuditRecordRepository,
    DecisionAuditRecordRepositoryError,
)


def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _to_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DuckDbDecisionAuditRecordRepository:
    """Thread-safe DuckDB adapter implementing DecisionAuditRecordRepository protocol.

    Persists DecisionAuditRecord instances append-only with strict idempotency and metadata validation.
    """

    def __init__(
        self,
        db_path: str = "data/database/decision_intelligence.duckdb",
        conn: Optional[duckdb.DuckDBPyConnection] = None,
        codec: Optional[DecisionAuditRecordCodec] = None,
    ) -> None:
        self._lock = threading.Lock()
        self._codec = codec or DecisionAuditRecordCodec()

        if conn is not None:
            self._conn = conn
        else:
            p = Path(db_path)
            if str(db_path) != ":memory:":
                p.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(db_path))

        self.initialize_schema()

    def initialize_schema(self) -> None:
        """Idempotently creates table schema and index."""
        with self._lock:
            try:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS decision_audit_records (
                        decision_id VARCHAR PRIMARY KEY,
                        generated_at TIMESTAMP NOT NULL,
                        recorded_at TIMESTAMP NOT NULL,
                        action VARCHAR NOT NULL,
                        severity VARCHAR NOT NULL,
                        confidence DOUBLE NOT NULL,
                        policy_version VARCHAR NOT NULL,
                        record_schema_version VARCHAR NOT NULL,
                        payload_json VARCHAR NOT NULL
                    );
                    """
                )
            except Exception as err:
                raise DecisionAuditRecordRepositoryError("Failed to initialize DuckDB schema") from err

    def save(self, record: DecisionAuditRecord) -> None:
        if not isinstance(record, DecisionAuditRecord):
            raise TypeError("record must be DecisionAuditRecord")

        canonical_payload = self._codec.encode(record)
        gen_naive = _to_naive_utc(record.context.generated_at)
        rec_naive = _to_naive_utc(record.recorded_at)

        with self._lock:
            try:
                # Check for existing record by decision_id
                cursor = self._conn.execute(
                    "SELECT payload_json FROM decision_audit_records WHERE decision_id = ?",
                    [record.decision_id],
                )
                row = cursor.fetchone()

                if row is not None:
                    existing_payload = row[0]
                    if existing_payload == canonical_payload:
                        # Idempotent no-op
                        return
                    else:
                        raise DecisionAuditRecordConflictError(
                            f"Record with decision_id '{record.decision_id}' already exists with different payload"
                        )

                # Insert new record in transaction
                self._conn.execute("BEGIN TRANSACTION;")
                self._conn.execute(
                    """
                    INSERT INTO decision_audit_records (
                        decision_id,
                        generated_at,
                        recorded_at,
                        action,
                        severity,
                        confidence,
                        policy_version,
                        record_schema_version,
                        payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '1.0', ?);
                    """,
                    [
                        record.decision_id,
                        gen_naive,
                        rec_naive,
                        record.policy_result.action.value,
                        record.policy_result.severity.value,
                        record.policy_result.confidence,
                        record.policy_result.policy_version,
                        canonical_payload,
                    ],
                )
                self._conn.execute("COMMIT;")
            except (DecisionAuditRecordConflictError, DecisionAuditRecordDataError):
                self._rollback_safe()
                raise
            except Exception as err:
                self._rollback_safe()
                raise DecisionAuditRecordRepositoryError("Failed to save DecisionAuditRecord") from err

    def get_by_id(self, decision_id: str) -> DecisionAuditRecord | None:
        if not isinstance(decision_id, str) or not decision_id.strip():
            raise ValueError("decision_id must be non-empty string")

        with self._lock:
            try:
                cursor = self._conn.execute(
                    """
                    SELECT decision_id, generated_at, recorded_at, action, severity, confidence, policy_version, record_schema_version, payload_json
                    FROM decision_audit_records
                    WHERE decision_id = ?;
                    """,
                    [decision_id],
                )
                row = cursor.fetchone()
                if row is None:
                    return None

                return self._parse_and_validate_row(row)
            except (DecisionAuditRecordDataError, ValueError):
                raise
            except Exception as err:
                raise DecisionAuditRecordRepositoryError("Failed to query get_by_id") from err

    def get_latest(self) -> DecisionAuditRecord | None:
        with self._lock:
            try:
                cursor = self._conn.execute(
                    """
                    SELECT decision_id, generated_at, recorded_at, action, severity, confidence, policy_version, record_schema_version, payload_json
                    FROM decision_audit_records
                    ORDER BY generated_at DESC, decision_id DESC
                    LIMIT 1;
                    """
                )
                row = cursor.fetchone()
                if row is None:
                    return None

                return self._parse_and_validate_row(row)
            except DecisionAuditRecordDataError:
                raise
            except Exception as err:
                raise DecisionAuditRecordRepositoryError("Failed to query get_latest") from err

    def list_records(self) -> tuple[DecisionAuditRecord, ...]:
        with self._lock:
            try:
                cursor = self._conn.execute(
                    """
                    SELECT decision_id, generated_at, recorded_at, action, severity, confidence, policy_version, record_schema_version, payload_json
                    FROM decision_audit_records
                    ORDER BY generated_at ASC, decision_id ASC;
                    """
                )
                rows = cursor.fetchall()
                if not rows:
                    return ()

                records = []
                for row in rows:
                    rec = self._parse_and_validate_row(row)
                    records.append(rec)

                return tuple(records)
            except DecisionAuditRecordDataError:
                raise
            except Exception as err:
                raise DecisionAuditRecordRepositoryError("Failed to query list_records") from err

    def _parse_and_validate_row(self, row: tuple) -> DecisionAuditRecord:
        (
            col_id,
            col_gen_at,
            col_rec_at,
            col_action,
            col_severity,
            col_conf,
            col_policy_ver,
            col_schema_ver,
            col_payload_json,
        ) = row

        if col_schema_ver != "1.0":
            raise DecisionAuditRecordDataError(f"Unsupported record schema version '{col_schema_ver}'")

        record = self._codec.decode(col_payload_json)

        # Validate index metadata matches payload
        if record.decision_id != col_id:
            raise DecisionAuditRecordDataError("Metadata decision_id mismatch")
        if _to_naive_utc(record.context.generated_at) != _to_naive_utc(col_gen_at if isinstance(col_gen_at, datetime) else datetime.fromisoformat(str(col_gen_at))):
            raise DecisionAuditRecordDataError("Metadata generated_at mismatch")
        if _to_naive_utc(record.recorded_at) != _to_naive_utc(col_rec_at if isinstance(col_rec_at, datetime) else datetime.fromisoformat(str(col_rec_at))):
            raise DecisionAuditRecordDataError("Metadata recorded_at mismatch")
        if record.policy_result.action.value != col_action:
            raise DecisionAuditRecordDataError("Metadata action mismatch")
        if record.policy_result.severity.value != col_severity:
            raise DecisionAuditRecordDataError("Metadata severity mismatch")
        if abs(record.policy_result.confidence - float(col_conf)) > 1e-6:
            raise DecisionAuditRecordDataError("Metadata confidence mismatch")
        if record.policy_result.policy_version != col_policy_ver:
            raise DecisionAuditRecordDataError("Metadata policy_version mismatch")

        return record


    def _rollback_safe(self) -> None:
        try:
            self._conn.execute("ROLLBACK;")
        except Exception:
            pass
