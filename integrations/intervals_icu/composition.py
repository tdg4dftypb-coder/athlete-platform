"""Explicit operator-controlled Intervals.icu persistence composition."""
from __future__ import annotations

from pathlib import Path

import duckdb

from .client import IntervalsClient
from .models import IntervalsConfiguration
from .persistence import IntervalsRepository, IntervalsSchema
from .service import IntervalsSyncService


DEFAULT_DATABASE_PATH = Path("data/database/intervals_icu.duckdb")


def initialize_intervals_schema(path=DEFAULT_DATABASE_PATH) -> None:
    """Create the provider store only during an explicit controlled operation."""
    connection = duckdb.connect(str(path))
    try:
        IntervalsSchema.create(connection)
    finally:
        connection.close()


def build_intervals_sync_service(connection, *, environ=None, transport=None):
    """Compose against an already-open, operator-selected connection."""
    configuration = IntervalsConfiguration.from_environment(environ)
    client = IntervalsClient(configuration, transport)
    return IntervalsSyncService(client, IntervalsRepository(connection))
