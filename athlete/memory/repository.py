import json
from datetime import datetime

from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
)
from core.database import Database


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
