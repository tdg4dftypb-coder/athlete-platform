import json
from datetime import datetime

import duckdb

from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
)
from core.database import Database


class DuplicateSourceIdentityError(Exception):
    """Raised when an event type already exists for a source identity."""

    def __init__(
        self,
        event_type: AthleteMemoryEventType,
        source_type: str,
        source_key: str,
    ) -> None:
        self.event_type = event_type
        self.source_type = source_type
        self.source_key = source_key
        super().__init__(
            "Duplicate event source identity: "
            f"{event_type.value}/{source_type}/{source_key}"
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
                    event.event_type,
                    event.source_type,
                    event.source_key,
                ) from error
            raise

    def get_by_source_identity(
        self,
        event_type: AthleteMemoryEventType,
        source_type: str,
        source_key: str,
    ) -> AthleteMemoryEvent | None:
        row = self.db.connection.execute(
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
            WHERE event_type = ? AND source_type = ? AND source_key = ?
            """,
            (event_type.value, source_type, source_key),
        ).fetchone()

        if row is None:
            return None
        return self._event_from_row(row)

    @staticmethod
    def _is_source_identity_conflict(error: duckdb.ConstraintException) -> bool:
        message = str(error)
        return all(
            field in message
            for field in ("event_type:", "source_type:", "source_key:")
        )

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

        return [self._event_from_row(row) for row in rows]

    @staticmethod
    def _event_from_row(row) -> AthleteMemoryEvent:
        return AthleteMemoryEvent(
            event_id=row[0],
            occurred_at=row[1],
            event_type=AthleteMemoryEventType(row[2]),
            source_type=row[3],
            source_key=row[4],
            schema_version=row[5],
            payload=json.loads(row[6]),
        )
