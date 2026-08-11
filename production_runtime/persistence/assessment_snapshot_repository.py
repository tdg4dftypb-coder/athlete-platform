"""Append-only DuckDB assessment snapshot storage in the runtime audit database."""
from __future__ import annotations

from datetime import timezone
from pathlib import Path
import threading

import duckdb

from production_runtime.assessment_snapshot import (
    AssessmentSnapshot,
    AssessmentSnapshotCodec,
    AssessmentSnapshotConflictError,
    AssessmentSnapshotIntegrityError,
    AssessmentSnapshotUnavailableError,
)


class DuckDbAssessmentSnapshotRepository:
    def __init__(self, db_path) -> None:
        self._db_path = str(db_path)
        self._codec = AssessmentSnapshotCodec()
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connection(self):
        try:
            if self._db_path != ":memory:":
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            return duckdb.connect(self._db_path)
        except Exception as error:
            raise AssessmentSnapshotUnavailableError("assessment snapshot store unavailable") from error

    def _ensure_schema(self) -> None:
        with self._lock:
            connection = self._connection()
            try:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS production_runtime_assessment_snapshots (
                        runtime_id VARCHAR PRIMARY KEY,
                        artifact_id VARCHAR NOT NULL,
                        target_local_date DATE NOT NULL,
                        created_at_utc TIMESTAMP NOT NULL,
                        snapshot_schema_version VARCHAR NOT NULL,
                        payload_json VARCHAR NOT NULL
                    )
                """)
                connection.execute("""
                    CREATE INDEX IF NOT EXISTS production_runtime_assessment_artifact_idx
                    ON production_runtime_assessment_snapshots (artifact_id)
                """)
            except Exception as error:
                raise AssessmentSnapshotUnavailableError("failed to initialize assessment snapshot store") from error
            finally:
                connection.close()

    def save(self, snapshot: AssessmentSnapshot) -> None:
        if not isinstance(snapshot, AssessmentSnapshot):
            raise TypeError("snapshot must be AssessmentSnapshot")
        payload = self._codec.encode(snapshot)
        with self._lock:
            connection = self._connection()
            try:
                row = connection.execute(
                    "SELECT payload_json FROM production_runtime_assessment_snapshots WHERE runtime_id = ?",
                    [snapshot.runtime_id],
                ).fetchone()
                if row is not None:
                    if row[0] == payload:
                        return
                    raise AssessmentSnapshotConflictError(
                        f"runtime '{snapshot.runtime_id}' already has a different assessment snapshot"
                    )
                connection.execute(
                    """INSERT INTO production_runtime_assessment_snapshots
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    [snapshot.runtime_id, snapshot.artifact_id, snapshot.target_local_date,
                     snapshot.created_at_utc.astimezone(timezone.utc).replace(tzinfo=None),
                     snapshot.schema_version, payload],
                )
            except AssessmentSnapshotConflictError:
                raise
            except Exception as error:
                raise AssessmentSnapshotUnavailableError("failed to persist assessment snapshot") from error
            finally:
                connection.close()

    def get_by_runtime_id(self, runtime_id: str) -> AssessmentSnapshot | None:
        return self._read("runtime_id", runtime_id)

    def get_by_artifact_id(self, artifact_id: str) -> AssessmentSnapshot | None:
        return self._read("artifact_id", artifact_id)

    def _read(self, column: str, value: str) -> AssessmentSnapshot | None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{column} must be non-empty")
        with self._lock:
            connection = self._connection()
            try:
                row = connection.execute(
                    f"SELECT runtime_id, artifact_id, target_local_date, snapshot_schema_version, payload_json "
                    f"FROM production_runtime_assessment_snapshots WHERE {column} = ?",
                    [value],
                ).fetchone()
                if row is None:
                    return None
                runtime_id, artifact_id, target_date, schema_version, payload = row
                if schema_version != self._codec.SCHEMA_VERSION:
                    raise AssessmentSnapshotIntegrityError("invalid assessment snapshot schema version")
                snapshot = self._codec.decode(payload)
                if snapshot.runtime_id != runtime_id:
                    raise AssessmentSnapshotIntegrityError("assessment snapshot runtime_id mismatch")
                if snapshot.artifact_id != artifact_id:
                    raise AssessmentSnapshotIntegrityError("assessment snapshot artifact mismatch")
                if snapshot.target_local_date != target_date:
                    raise AssessmentSnapshotIntegrityError("assessment snapshot target date mismatch")
                return snapshot
            except AssessmentSnapshotIntegrityError:
                raise
            except Exception as error:
                raise AssessmentSnapshotUnavailableError("failed to read assessment snapshot") from error
            finally:
                connection.close()
