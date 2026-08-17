from __future__ import annotations

from datetime import timezone
import json


def naive(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class ZwiftFitSchema:
    @staticmethod
    def create(connection):
        connection.execute("""
            CREATE TABLE IF NOT EXISTS zwift_fit_artifacts (
                artifact_hash VARCHAR PRIMARY KEY, artifact_reference VARCHAR NOT NULL,
                size_bytes BIGINT NOT NULL, source_mtime TIMESTAMP NOT NULL,
                ingested_at TIMESTAMP NOT NULL, workout_record_key VARCHAR NOT NULL,
                candidate_json VARCHAR NOT NULL, candidate_fingerprint VARCHAR NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS zwift_fit_sync_audit (
                started_at TIMESTAMP NOT NULL, completed_at TIMESTAMP NOT NULL,
                discovered INTEGER NOT NULL, ready INTEGER NOT NULL,
                ingested INTEGER NOT NULL, duplicate INTEGER NOT NULL,
                skipped_not_stable INTEGER NOT NULL, malformed INTEGER NOT NULL,
                failed INTEGER NOT NULL
            )
        """)


class ZwiftFitRepository:
    def __init__(self, connection):
        self.connection = connection

    def contains(self, artifact_hash):
        return self.connection.execute(
            "SELECT COUNT(*) FROM zwift_fit_artifacts WHERE artifact_hash=?", [artifact_hash]
        ).fetchone()[0] > 0

    def save(self, artifact_hash, reference, stat, ingested_at, record_key, candidate):
        self.connection.execute(
            "INSERT INTO zwift_fit_artifacts VALUES (?,?,?,?,?,?,?,?)",
            [artifact_hash, reference, stat.st_size,
             datetime_from_timestamp(stat.st_mtime), naive(ingested_at), record_key,
             json.dumps(candidate.serialize(), sort_keys=True, separators=(",", ":")),
             candidate.fingerprint],
        )

    def audit(self, result):
        self.connection.execute(
            "INSERT INTO zwift_fit_sync_audit VALUES (?,?,?,?,?,?,?,?,?)",
            [naive(result.started_at), naive(result.completed_at), result.discovered,
             result.ready, result.ingested, result.duplicate, result.skipped_not_stable,
             result.malformed, result.failed],
        )


def datetime_from_timestamp(value):
    from datetime import datetime
    return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None)
