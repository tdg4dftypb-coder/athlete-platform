"""Transactional canonical persistence for HealthKit source records."""
from __future__ import annotations

from datetime import timezone
from hashlib import sha256
import json

from core.database import Database
from health_ingestion.models import HealthKitBatch, HealthKitSourceRecord


class HealthKitIngestionSchema:
    @staticmethod
    def create(database: Database) -> None:
        connection = database.connection
        connection.execute("ALTER TABLE health_records ADD COLUMN IF NOT EXISTS provider VARCHAR")
        connection.execute("ALTER TABLE health_records ADD COLUMN IF NOT EXISTS external_id VARCHAR")
        connection.execute("ALTER TABLE health_records ADD COLUMN IF NOT EXISTS deleted BOOLEAN DEFAULT FALSE")
        connection.execute("ALTER TABLE health_records ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS health_records_provider_identity "
            "ON health_records(provider, external_id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS healthkit_ingestion_batches (
                batch_id VARCHAR PRIMARY KEY,
                payload_hash VARCHAR NOT NULL,
                accepted INTEGER NOT NULL,
                duplicate INTEGER NOT NULL,
                rejected INTEGER NOT NULL,
                rejected_external_ids_json VARCHAR NOT NULL,
                received_at TIMESTAMP NOT NULL
            )
            """
        )


class HealthKitBatchCollisionError(RuntimeError):
    pass


class HealthKitRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    @staticmethod
    def payload_hash(batch: HealthKitBatch) -> str:
        canonical = json.dumps(
            {
                "batch_id": batch.batch_id,
                "device_id": batch.device_id,
                "records": [record.__dict__ | {
                    "start_at": None if record.start_at is None else record.start_at.isoformat(),
                    "end_at": None if record.end_at is None else record.end_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                } for record in batch.records],
            },
            sort_keys=True, separators=(",", ":"),
        )
        return "sha256:" + sha256(canonical.encode()).hexdigest()

    def existing_batch(self, batch: HealthKitBatch):
        row = self._database.connection.execute(
            "SELECT payload_hash, accepted, duplicate, rejected, "
            "rejected_external_ids_json, received_at "
            "FROM healthkit_ingestion_batches WHERE batch_id = ?", [batch.batch_id]
        ).fetchone()
        if row is None:
            return None
        if row[0] == self.payload_hash(batch) or self._is_legacy_match(batch, row):
            return row
        raise HealthKitBatchCollisionError("batch identity collision")

    def _is_legacy_match(self, batch: HealthKitBatch, row: tuple) -> bool:
        if row[3] > 0 or not batch.records:
            return False
        if row[1] + row[2] != len(batch.records):
            return False
        connection = self._database.connection
        for record in batch.records:
            stored = connection.execute(
                "SELECT record_type, source_name, unit, start_date, end_date, numeric_value, text_value, deleted, updated_at "
                "FROM health_records WHERE provider = 'healthkit' AND external_id = ?",
                [record.external_id],
            ).fetchone()
            if stored is None:
                return False
            expected = (
                record.sample_type,
                record.source_name,
                record.unit,
                self._date_text(record.start_at),
                self._date_text(record.end_at),
                record.value,
                record.workout_sport,
                record.deleted,
                record.updated_at.astimezone(timezone.utc).replace(tzinfo=None),
            )
            if stored != expected:
                return False
        return True

    def persist(self, batch: HealthKitBatch, received_at, rejected_ids=()) -> tuple[int, int]:
        connection = self._database.connection
        connection.execute("BEGIN TRANSACTION")
        try:
            accepted = duplicate = 0
            for record in batch.records:
                existing = connection.execute(
                    "SELECT record_type, start_date, end_date, numeric_value, unit, text_value, deleted, updated_at "
                    "FROM health_records WHERE provider = 'healthkit' AND external_id = ?",
                    [record.external_id],
                ).fetchone()
                projected = self._project(record)
                if existing == projected:
                    duplicate += 1
                    continue
                connection.execute(
                    "DELETE FROM health_records WHERE provider = 'healthkit' AND external_id = ?",
                    [record.external_id],
                )
                connection.execute(
                    """
                    INSERT INTO health_records (
                        record_type, source_name, unit, start_date, end_date,
                        numeric_value, text_value, provider, external_id, deleted, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'healthkit', ?, ?, ?)
                    """,
                    [
                        record.sample_type, record.source_name, record.unit,
                        self._date_text(record.start_at), self._date_text(record.end_at),
                        record.value, record.workout_sport, record.external_id, record.deleted,
                        record.updated_at.astimezone(timezone.utc).replace(tzinfo=None),
                    ],
                )
                accepted += 1
            connection.execute(
                "INSERT INTO healthkit_ingestion_batches VALUES (?, ?, ?, ?, ?, ?, ?)",
                [batch.batch_id, self.payload_hash(batch), accepted, duplicate,
                 len(rejected_ids), json.dumps(list(rejected_ids), separators=(",", ":")),
                 received_at.astimezone(timezone.utc).replace(tzinfo=None)],
            )
            connection.execute("COMMIT")
            return accepted, duplicate
        except Exception:
            connection.execute("ROLLBACK")
            raise

    @staticmethod
    def _date_text(value):
        return None if value is None else value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S +0000")

    @classmethod
    def _project(cls, record: HealthKitSourceRecord):
        return (
            record.sample_type, cls._date_text(record.start_at), cls._date_text(record.end_at),
            record.value, record.unit, record.workout_sport, record.deleted,
            record.updated_at.astimezone(timezone.utc).replace(tzinfo=None),
        )
