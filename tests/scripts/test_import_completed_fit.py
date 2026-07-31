from datetime import datetime, timedelta
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
    assert result.event.source_key == parsed_activity.start.isoformat()
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


def test_import_refuses_the_production_database_path(tmp_path):
    with pytest.raises(ValueError, match="Refusing to import"):
        import_completed_fit.import_completed_fit(
            tmp_path / "completed.fit",
            import_completed_fit.PRODUCTION_DATABASE_PATH,
            "recovery_60",
        )
