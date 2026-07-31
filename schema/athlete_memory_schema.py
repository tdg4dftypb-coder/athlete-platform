from core.database import Database


class AthleteMemorySchema:

    def __init__(
        self,
        db: Database | None = None,
    ) -> None:

        self.db = db or Database()

    def create(self) -> None:

        self.db.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_memory_events (
                event_id VARCHAR PRIMARY KEY,
                occurred_at TIMESTAMP NOT NULL,
                event_type VARCHAR NOT NULL,
                source_type VARCHAR NOT NULL,
                source_key VARCHAR NOT NULL,
                schema_version INTEGER NOT NULL,
                payload_json VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db.connection.execute(
            "DROP INDEX IF EXISTS athlete_memory_events_source_key_unique"
        )
        self.db.connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            athlete_memory_events_source_identity_unique
            ON athlete_memory_events (source_type, source_key)
            """
        )
