import json
from datetime import datetime

import duckdb

from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
)
from core.database import Database


class DuplicateSourceIdentityError(Exception):
    """Raised when a source provider and external identifier already exist."""

    def __init__(self, source_type: str, source_key: str) -> None:
        self.source_type = source_type
        self.source_key = source_key
        super().__init__(
            f"Duplicate source identity: {source_type}/{source_key}"
        )


class AthleteMemoryRepository:

    def __init__(
        self,
        db: Database | None = None,
    ) -> None:

        self.db = db or Database()

    def append(
        self,
        event: AthleteMemoryEvent,
    ) -> None:

        try:
            self.db.connection.execute(
                """
                INSERT INTO athlete_memory_events
                (
                    event_id,
                    occurred_at,
                    event_type,
                    source_type,
                    source_key,
                    schema_version,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.occurred_at,
                    event.event_type.value,
                    event.source_type,
                    event.source_key,
                    event.schema_version,
                    json.dumps(event.payload, ensure_ascii=False),
                ),
            )
        except duckdb.ConstraintException as error:
            if self._is_source_identity_conflict(error):
                raise DuplicateSourceIdentityError(
                    event.source_type,
                    event.source_key,
                ) from error
            raise

    @staticmethod
    def _is_source_identity_conflict(error: duckdb.ConstraintException) -> bool:
        message = str(error)
        return "source_type:" in message and "source_key:" in message

    def load_between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[AthleteMemoryEvent]:

        rows = self.db.connection.execute(
            """
            SELECT
                event_id,
                occurred_at,
                event_type,
                source_type,
                source_key,
                schema_version,
                payload_json
            FROM athlete_memory_events
            WHERE occurred_at BETWEEN ? AND ?
            ORDER BY occurred_at
            """,
            (start, end),
        ).fetchall()

        return [
            AthleteMemoryEvent(
                event_id=event_id,
                occurred_at=occurred_at,
                event_type=AthleteMemoryEventType(event_type),
                source_type=source_type,
                source_key=source_key,
                schema_version=schema_version,
                payload=json.loads(payload_json),
            )
            for (
                event_id,
                occurred_at,
                event_type,
                source_type,
                source_key,
                schema_version,
                payload_json,
            ) in rows
        ]
