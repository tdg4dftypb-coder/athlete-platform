"""Transactional provider-owned activity facts and synchronization audit."""
from __future__ import annotations

from datetime import timezone
from hashlib import sha256
import json

from .errors import PersistenceFailure
from .models import CONTRACT_VERSION, IntervalsActivity, PROVIDER


def naive(value):
    return None if value is None else value.astimezone(timezone.utc).replace(tzinfo=None)


class IntervalsSchema:
    @staticmethod
    def create(connection) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS intervals_icu_activities (
                provider VARCHAR NOT NULL, external_id VARCHAR NOT NULL,
                contract_version VARCHAR NOT NULL, updated_at TIMESTAMP NOT NULL,
                start_at TIMESTAMP NOT NULL, end_at TIMESTAMP NOT NULL,
                sport VARCHAR NOT NULL, duration_seconds DOUBLE NOT NULL,
                distance_meters DOUBLE, intervals_external_tss DOUBLE,
                intervals_external_intensity DOUBLE, average_heart_rate DOUBLE,
                average_power DOUBLE, weighted_average_power DOUBLE,
                average_cadence DOUBLE, archived BOOLEAN NOT NULL,
                semantic_hash VARCHAR NOT NULL, PRIMARY KEY(provider, external_id)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS intervals_icu_sync_state (
                provider VARCHAR PRIMARY KEY, watermark TIMESTAMP,
                last_attempt_at TIMESTAMP, last_successful_sync_at TIMESTAMP,
                last_error_code VARCHAR
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS intervals_icu_sync_audit (
                sync_id VARCHAR PRIMARY KEY, started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP NOT NULL, status VARCHAR NOT NULL,
                fetched INTEGER NOT NULL, inserted INTEGER NOT NULL,
                updated INTEGER NOT NULL, unchanged INTEGER NOT NULL,
                archived INTEGER NOT NULL, rejected INTEGER NOT NULL,
                watermark_before TIMESTAMP, watermark_after TIMESTAMP,
                error_code VARCHAR
            )
        """)


class IntervalsRepository:
    def __init__(self, connection):
        self.connection = connection

    def watermark(self):
        row = self.connection.execute(
            "SELECT watermark FROM intervals_icu_sync_state WHERE provider = ?", [PROVIDER]
        ).fetchone()
        return None if row is None or row[0] is None else row[0].replace(tzinfo=timezone.utc)

    @staticmethod
    def semantic_hash(activity: IntervalsActivity) -> str:
        payload = {
            key: (value.isoformat() if hasattr(value, "isoformat") else
                  value.value if hasattr(value, "value") else value)
            for key, value in activity.__dict__.items()
        }
        return "sha256:" + sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def persist_slice(self, records, *, started_at, completed_at, watermark_before, watermark_after,
                      rejected=0, sync_id: str):
        connection = self.connection
        connection.execute("BEGIN TRANSACTION")
        try:
            inserted = updated = unchanged = archived = 0
            for record in records:
                fingerprint = self.semantic_hash(record)
                existing = connection.execute(
                    "SELECT semantic_hash FROM intervals_icu_activities WHERE provider=? AND external_id=?",
                    [PROVIDER, record.external_id],
                ).fetchone()
                if existing and existing[0] == fingerprint:
                    unchanged += 1
                    continue
                values = [PROVIDER, record.external_id, CONTRACT_VERSION, naive(record.updated_at),
                          naive(record.start_at), naive(record.end_at), record.sport.value,
                          record.duration_seconds, record.distance_meters, record.intervals_external_tss,
                          record.intervals_external_intensity, record.average_heart_rate,
                          record.average_power, record.weighted_average_power, record.average_cadence,
                          record.archived, fingerprint]
                if existing:
                    connection.execute("DELETE FROM intervals_icu_activities WHERE provider=? AND external_id=?",
                                       [PROVIDER, record.external_id])
                    updated += 1
                else:
                    inserted += 1
                connection.execute("INSERT INTO intervals_icu_activities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
                archived += int(record.archived)
            connection.execute("DELETE FROM intervals_icu_sync_state WHERE provider=?", [PROVIDER])
            connection.execute("INSERT INTO intervals_icu_sync_state VALUES (?,?,?,?,NULL)",
                               [PROVIDER, naive(watermark_after), naive(completed_at), naive(completed_at)])
            connection.execute("INSERT INTO intervals_icu_sync_audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                               [sync_id, naive(started_at), naive(completed_at), "SUCCESS", len(records),
                                inserted, updated, unchanged, archived, rejected,
                                naive(watermark_before), naive(watermark_after)])
            connection.execute("COMMIT")
            return inserted, updated, unchanged, archived
        except Exception as error:
            connection.execute("ROLLBACK")
            raise PersistenceFailure("Intervals.icu persistence failed") from error

    def record_failed_attempt(self, at, code):
        self.connection.execute(
            """
            INSERT INTO intervals_icu_sync_state VALUES (?, NULL, ?, NULL, ?)
            ON CONFLICT(provider) DO UPDATE SET
                last_attempt_at=excluded.last_attempt_at,
                last_error_code=excluded.last_error_code
            """,
            [PROVIDER, naive(at), code],
        )
