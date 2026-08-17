"""Explicit, side-effect-free-until-called Context Memory composition."""
from pathlib import Path

import duckdb

from application.athlete_context_memory import (
    AthleteContextMemoryService,
    build_athlete_context_memory_service,
)
from athlete.context_memory.paths import get_default_context_memory_db_path
from athlete.context_memory.persistence import (
    AthleteContextMemorySchema,
    DuckDbContextMemoryRepository,
)


def initialize_context_memory_schema(
    db_path: str | Path | None = None,
) -> Path:
    """Explicitly create only Context Memory tables at the resolved path."""

    resolved = get_default_context_memory_db_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(resolved))
    try:
        AthleteContextMemorySchema.create(connection)
    finally:
        connection.close()
    return resolved


def build_context_memory_read_service(
    db_path: str | Path | None = None,
) -> AthleteContextMemoryService:
    """Build the read service without opening a DB or initializing schema."""

    resolved = get_default_context_memory_db_path(db_path)
    repository = DuckDbContextMemoryRepository(
        resolved,
        initialize_schema=False,
    )
    return build_athlete_context_memory_service(repository)
