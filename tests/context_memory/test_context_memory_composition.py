from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

from application.athlete_context_memory import (
    AthleteContextMemoryReadError,
    CoachMemoryContextQuery,
)
from athlete.context_memory.composition import (
    build_context_memory_read_service,
    initialize_context_memory_schema,
)


NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)
CONTEXT_TABLES = {
    "athlete_context_memory_actions",
    "athlete_context_memory_items",
    "athlete_context_memory_tombstones",
}


def table_names(path: Path) -> set[str]:
    connection = duckdb.connect(str(path), read_only=True)
    try:
        return {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
    finally:
        connection.close()


def test_import_and_read_service_construction_do_not_create_database(tmp_path):
    path = tmp_path / "not-created.duckdb"
    service = build_context_memory_read_service(path)
    assert service is not None
    assert not path.exists()


def test_explicit_initialization_creates_only_context_tables_and_is_idempotent(tmp_path):
    path = tmp_path / "context.duckdb"
    assert initialize_context_memory_schema(path) == path
    first = table_names(path)
    assert first == CONTEXT_TABLES
    assert initialize_context_memory_schema(path) == path
    assert table_names(path) == first


def test_initialization_preserves_legacy_table_schema_and_data(tmp_path):
    path = tmp_path / "legacy.duckdb"
    connection = duckdb.connect(str(path))
    connection.execute(
        "CREATE TABLE athlete_memory_events(event_id VARCHAR, event_type VARCHAR)"
    )
    connection.execute(
        "INSERT INTO athlete_memory_events VALUES (?, ?)",
        ["legacy:1", "ACTIVITY_RECORDED"],
    )
    before_schema = connection.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'athlete_memory_events' ORDER BY ordinal_position"
    ).fetchall()
    connection.close()

    initialize_context_memory_schema(path)

    connection = duckdb.connect(str(path), read_only=True)
    try:
        after_schema = connection.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'athlete_memory_events' ORDER BY ordinal_position"
        ).fetchall()
        rows = connection.execute("SELECT * FROM athlete_memory_events").fetchall()
    finally:
        connection.close()
    assert after_schema == before_schema
    assert rows == [("legacy:1", "ACTIVITY_RECORDED")]
    assert table_names(path) == CONTEXT_TABLES | {"athlete_memory_events"}


def test_read_service_query_does_not_mutate_schema(tmp_path):
    path = tmp_path / "read-only-contract.duckdb"
    initialize_context_memory_schema(path)
    before = table_names(path)
    service = build_context_memory_read_service(path)
    context = service.get_coach_memory_context(
        CoachMemoryContextQuery("athlete:primary", NOW)
    )
    assert context.source_memory_ids == ()
    assert table_names(path) == before


def test_missing_schema_is_typed_application_failure_and_creates_no_file(tmp_path):
    path = tmp_path / "missing-parent" / "missing.duckdb"
    service = build_context_memory_read_service(path)
    with pytest.raises(AthleteContextMemoryReadError) as captured:
        service.get_coach_memory_context(
            CoachMemoryContextQuery("athlete:primary", NOW)
        )
    assert str(captured.value) == "durable athlete memory could not be read"
    assert str(path) not in str(captured.value)
    assert not path.exists()


def test_malformed_persisted_record_maps_to_typed_application_failure(tmp_path):
    path = tmp_path / "malformed.duckdb"
    initialize_context_memory_schema(path)
    connection = duckdb.connect(str(path))
    connection.execute(
        """
        INSERT INTO athlete_context_memory_items VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        [
            "memory:sha256:" + "0" * 64,
            "athlete:primary",
            "PREFERENCE",
            "TRAINING",
            "{}",
            "EXPLICIT",
            "ACTIVE",
            "NORMAL",
            "user",
            None,
            "[]",
            None,
            None,
            NOW.replace(tzinfo=None),
            None,
            NOW.replace(tzinfo=None),
            None,
            None,
            None,
            "1.0",
            "{}",
            "not-json",
        ],
    )
    connection.close()
    service = build_context_memory_read_service(path)
    with pytest.raises(AthleteContextMemoryReadError) as captured:
        service.get_coach_memory_context(
            CoachMemoryContextQuery("athlete:primary", NOW)
        )
    assert str(captured.value) == "durable athlete memory could not be read"
