from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from athlete.memory.models import AthleteMemoryEventType, DateRange
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from scripts import import_completed_fit
from training.ingestion.parsed_activity import ParsedActivity, ParsedActivityRecord


def build_parsed_activity() -> ParsedActivity:
    start = datetime(2026, 7, 30, 8, 0)

    return ParsedActivity(
        start=start,
        end=start + timedelta(minutes=5),
        sport="cycling",
        distance=3.0,
        calories=100,
        records=[
            ParsedActivityRecord(
                timestamp=start,
                power=200,
                heart_rate=140,
                cadence=90,
                speed=30.0,
            ),
            ParsedActivityRecord(
                timestamp=start + timedelta(seconds=299),
                power=210,
                heart_rate=145,
                cadence=92,
                speed=31.0,
            ),
        ],
    )


def test_import_records_one_fit_activity_in_the_explicit_temporary_database(
    tmp_path,
    monkeypatch,
    capsys,
):
    fit_path = tmp_path / "completed.fit"
    database_path = tmp_path / "athlete_memory.duckdb"
    fit_payload = b"completed FIT artifact"
    fit_path.write_bytes(fit_payload)
    parsed_activity = build_parsed_activity()
    created_database_paths = []
    real_database = Database

    monkeypatch.setattr(
        import_completed_fit,
        "FitParser",
        lambda: SimpleNamespace(parse=lambda _: parsed_activity),
    )

    def temporary_database(path):
        created_database_paths.append(Path(path))
        return real_database(path)

    monkeypatch.setattr(import_completed_fit, "Database", temporary_database)

    result = import_completed_fit.import_completed_fit(
        fit_path,
        database_path,
        "recovery_60",
    )

    assert result is not None
    assert result.event.event_type is AthleteMemoryEventType.WORKOUT_COMPLETED
    assert result.event.source_type == "fit_file"
    assert result.event.source_key == f"sha256:{sha256(fit_payload).hexdigest()}"
    assert created_database_paths == [database_path]

    database = Database(database_path)
    repository = AthleteMemoryRepository(database)
    events = repository.load_between(
        parsed_activity.start,
        parsed_activity.end + timedelta(microseconds=1),
    )
    snapshot = AthleteMemoryReader(repository).read(
        DateRange(
            start=parsed_activity.start,
            end=parsed_activity.end + timedelta(microseconds=1),
        )
    )

    assert len(events) == 1
    assert len(snapshot.workout_observations) == 1
    assert snapshot.source_event_ids == (result.event.event_id,)

    database.close()

    skipped = import_completed_fit.import_completed_fit(
        fit_path,
        database_path,
        "recovery_60",
    )

    assert skipped is None
    assert "SKIPPED: already imported" in capsys.readouterr().out


def test_import_recognizes_identical_fit_bytes_under_a_different_name(tmp_path, monkeypatch, capsys):
    database_path = tmp_path / "athlete_memory.duckdb"
    original = tmp_path / "original.fit"
    copy = tmp_path / "renamed-copy.fit"
    original.write_bytes(b"same FIT artifact")
    copy.write_bytes(b"same FIT artifact")
    parsed_activity = build_parsed_activity()

    monkeypatch.setattr(
        import_completed_fit,
        "FitParser",
        lambda: SimpleNamespace(parse=lambda _: parsed_activity),
    )

    first = import_completed_fit.import_completed_fit(
        original,
        database_path,
        "recovery_60",
    )
    duplicate = import_completed_fit.import_completed_fit(
        copy,
        database_path,
        "recovery_60",
    )

    assert first is not None
    assert duplicate is None
    assert "SKIPPED: already imported" in capsys.readouterr().out


def test_import_allows_different_fit_bytes_with_the_same_activity_start(tmp_path, monkeypatch):
    database_path = tmp_path / "athlete_memory.duckdb"
    first_path = tmp_path / "first.fit"
    second_path = tmp_path / "second.fit"
    first_path.write_bytes(b"first FIT artifact")
    second_path.write_bytes(b"second FIT artifact")
    parsed_activity = build_parsed_activity()

    monkeypatch.setattr(
        import_completed_fit,
        "FitParser",
        lambda: SimpleNamespace(parse=lambda _: parsed_activity),
    )

    first = import_completed_fit.import_completed_fit(
        first_path,
        database_path,
        "recovery_60",
    )
    second = import_completed_fit.import_completed_fit(
        second_path,
        database_path,
        "recovery_60",
    )

    assert first is not None
    assert second is not None
    assert first.event.source_key != second.event.source_key

    database = Database(database_path)
    repository = AthleteMemoryRepository(database)
    events = repository.load_between(
        parsed_activity.start,
        parsed_activity.end + timedelta(microseconds=1),
    )

    assert len(events) == 2
    database.close()


def test_parser_error_leaves_no_database_or_partial_event(tmp_path, monkeypatch):
    fit_path = tmp_path / "completed.fit"
    database_path = tmp_path / "athlete_memory.duckdb"
    fit_path.write_bytes(b"valid source artifact")

    monkeypatch.setattr(
        import_completed_fit,
        "FitParser",
        lambda: SimpleNamespace(
            parse=lambda _: (_ for _ in ()).throw(RuntimeError("parse failed")),
        ),
    )

    with pytest.raises(RuntimeError, match="parse failed"):
        import_completed_fit.import_completed_fit(
            fit_path,
            database_path,
            "recovery_60",
        )

    assert not database_path.exists()


def test_append_failure_leaves_no_new_event(tmp_path, monkeypatch):
    fit_path = tmp_path / "completed.fit"
    database_path = tmp_path / "athlete_memory.duckdb"
    fit_path.write_bytes(b"valid source artifact")
    parsed_activity = build_parsed_activity()

    monkeypatch.setattr(
        import_completed_fit,
        "FitParser",
        lambda: SimpleNamespace(parse=lambda _: parsed_activity),
    )

    class FailingWriter:
        def __init__(self, repository):
            self.repository = repository

        def write(self, result, source_identity):
            raise RuntimeError("append failed")

    monkeypatch.setattr(import_completed_fit, "AthleteMemoryWriter", FailingWriter)

    with pytest.raises(RuntimeError, match="append failed"):
        import_completed_fit.import_completed_fit(
            fit_path,
            database_path,
            "recovery_60",
        )

    database = Database(database_path)
    event_count = database.connection.execute(
        "SELECT COUNT(*) FROM athlete_memory_events"
    ).fetchone()[0]

    assert event_count == 0
    database.close()


def test_post_write_reader_failure_reports_the_persisted_event_and_retry_is_duplicate(
    tmp_path,
    monkeypatch,
):
    fit_path = tmp_path / "completed.fit"
    database_path = tmp_path / "athlete_memory.duckdb"
    fit_path.write_bytes(b"valid source artifact")
    parsed_activity = build_parsed_activity()
    original_reader = import_completed_fit.AthleteMemoryReader

    monkeypatch.setattr(
        import_completed_fit,
        "FitParser",
        lambda: SimpleNamespace(parse=lambda _: parsed_activity),
    )

    class FailingReader:
        def __init__(self, repository):
            self.repository = repository

        def read(self, period):
            raise RuntimeError("read model unavailable")

    monkeypatch.setattr(import_completed_fit, "AthleteMemoryReader", FailingReader)

    with pytest.raises(
        import_completed_fit.PostWriteVerificationError,
        match="WORKOUT_COMPLETED was recorded, but post-write verification/read failed",
    ) as error:
        import_completed_fit.import_completed_fit(
            fit_path,
            database_path,
            "recovery_60",
        )

    database = Database(database_path)
    repository = AthleteMemoryRepository(database)
    events = repository.load_between(
        parsed_activity.start,
        parsed_activity.end + timedelta(microseconds=1),
    )

    assert len(events) == 1
    assert error.value.result.event == events[0]
    database.close()

    monkeypatch.setattr(import_completed_fit, "AthleteMemoryReader", original_reader)

    assert import_completed_fit.import_completed_fit(
        fit_path,
        database_path,
        "recovery_60",
    ) is None


def test_import_refuses_the_production_database_path(tmp_path):
    with pytest.raises(ValueError, match="Refusing to import"):
        import_completed_fit.import_completed_fit(
            tmp_path / "completed.fit",
            import_completed_fit.PRODUCTION_DATABASE_PATH,
            "recovery_60",
        )
