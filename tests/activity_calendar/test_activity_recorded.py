from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from activity_calendar.read_model import ActivityCalendarBuilder
from application.activity_fact_backfill import HistoricalActivityFactBackfill
from athlete.memory.activity_recorded import (
    ActivityRecordedSerializer,
    ActivityRecordedWriter,
    RecordedActivityFacts,
)
from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
    DateRange,
)
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from schema.athlete_memory_schema import AthleteMemorySchema
from schema.training_schema import TrainingSchema
from scripts.imports.import_workouts import import_workouts
from training.ingestion.fit_file_source_identity import FitFileSourceIdentity
from training.ingestion.source_identity import SourceIdentity
from repositories.workout_repository import WorkoutRepository


class EmptyPlanProvider:
    def get_planned_sessions(self, target_date):
        return ()


def facts(**overrides):
    values = {
        "start": datetime(2026, 8, 1, 22, 30, tzinfo=timezone.utc),
        "end": datetime(2026, 8, 1, 23, 30, tzinfo=timezone.utc),
        "sport": "cycling",
        "duration": 3600,
        "distance": 25000.0,
        "calories": 500,
        "tss": 55.0,
        "normalized_power": 210.0,
        "intensity_factor": 0.75,
    }
    values.update(overrides)
    return RecordedActivityFacts(**values)


def temporary_repositories(tmp_path):
    database = Database(tmp_path / "activities.duckdb")
    TrainingSchema(database).create()
    AthleteMemorySchema(database).create()
    return (
        database,
        WorkoutRepository(database),
        AthleteMemoryRepository(database),
    )


def insert_workout(
    database,
    file_name,
    start,
    *,
    duration=3600,
    end=None,
):
    end = end if end is not None else start + timedelta(seconds=abs(duration or 0))
    database.connection.execute(
        """
        INSERT INTO workouts (
            file_name, start_time, end_time, sport, duration, distance,
            calories, normalized_power, intensity_factor, tss
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            file_name,
            start,
            end,
            "cycling",
            duration,
            25000.0,
            500,
            210.0,
            0.75,
            55.0,
        ],
    )


def test_activity_recorded_serializer_has_explicit_factual_schema():
    payload = ActivityRecordedSerializer().serialize(facts())

    assert payload == {
        "schema_version": 1,
        "activity": {
            "start": "2026-08-01T22:30:00+00:00",
            "end": "2026-08-01T23:30:00+00:00",
            "sport": "cycling",
            "duration": 3600,
            "distance": 25000.0,
            "calories": 500,
        },
        "workout_summary": {
            "tss": 55.0,
            "normalized_power": 210.0,
            "intensity_factor": 0.75,
        },
    }
    assert "execution" not in payload
    assert "feedback" not in payload
    assert "workout" not in payload


def test_optional_metrics_remain_null():
    payload = ActivityRecordedSerializer().serialize(
        facts(tss=None, normalized_power=None, intensity_factor=None)
    )

    assert payload["workout_summary"] == {
        "tss": None,
        "normalized_power": None,
        "intensity_factor": None,
    }


def test_writer_preserves_source_identity_and_is_idempotent(tmp_path):
    database, _, repository = temporary_repositories(tmp_path)
    identity = SourceIdentity("fit_file", "sha256:abc")
    writer = ActivityRecordedWriter(repository)

    first = writer.write(facts(), identity)
    second = writer.write(facts(), identity)

    assert first.created is True
    assert second.created is False
    assert second.event.event_id == first.event.event_id
    assert first.event.event_type is AthleteMemoryEventType.ACTIVITY_RECORDED
    assert first.event.source_type == "fit_file"
    assert first.event.source_key == "sha256:abc"
    assert len(repository.load_between(facts().start, facts().end)) == 1
    database.close()


def test_activity_recorded_can_coexist_with_workout_completed_identity(tmp_path):
    database, _, repository = temporary_repositories(tmp_path)
    existing = AthleteMemoryEvent(
        event_id="workout-event",
        occurred_at=facts().end,
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="fit_file",
        source_key="sha256:same",
        schema_version=1,
        payload={},
    )
    repository.append(existing)

    result = ActivityRecordedWriter(repository).write(
        facts(), SourceIdentity("fit_file", "sha256:same")
    )

    assert result.created is True
    assert result.event.event_id != existing.event_id
    assert result.event.event_type is AthleteMemoryEventType.ACTIVITY_RECORDED
    assert len(repository.load_between(facts().start, facts().end)) == 2
    database.close()


def test_workout_reader_ignores_factual_events_without_weakening_v1(tmp_path):
    database, _, repository = temporary_repositories(tmp_path)
    ActivityRecordedWriter(repository).write(
        facts(), SourceIdentity("fit_file", "sha256:fact")
    )

    snapshot = AthleteMemoryReader(repository).read(
        DateRange(facts().start, facts().end + timedelta(seconds=1))
    )

    assert snapshot.workout_observations == ()
    assert snapshot.source_event_ids == ()
    database.close()


def test_backfill_is_bounded_dry_run_and_idempotent(tmp_path):
    database, workouts, events = temporary_repositories(tmp_path)
    fit_directory = tmp_path / "fits"
    fit_directory.mkdir()
    start = datetime(2026, 8, 1, 8, 30)
    insert_workout(database, "valid.fit", start)
    insert_workout(database, "missing.fit", start + timedelta(hours=1))
    insert_workout(database, "ambiguous.fit", start + timedelta(hours=2))
    insert_workout(database, "malformed.fit", start + timedelta(hours=3), duration=-1)
    insert_workout(database, "outside.fit", datetime(2026, 8, 2, 0, 0))
    (fit_directory / "valid.fit").write_bytes(b"valid")
    (fit_directory / "one").mkdir()
    (fit_directory / "two").mkdir()
    (fit_directory / "one" / "ambiguous.fit").write_bytes(b"one")
    (fit_directory / "two" / "ambiguous.fit").write_bytes(b"two")
    backfill = HistoricalActivityFactBackfill(workouts, events, fit_directory)

    dry_run = backfill.run(date(2026, 8, 1), date(2026, 8, 1))
    applied = backfill.run(
        date(2026, 8, 1), date(2026, 8, 1), dry_run=False
    )
    repeated = backfill.run(
        date(2026, 8, 1), date(2026, 8, 1), dry_run=False
    )

    assert dry_run.scanned == 4
    assert dry_run.eligible == 3
    assert dry_run.identity_matched == 1
    assert dry_run.would_create == 1
    assert dry_run.skipped == 3
    assert dry_run.created == 0
    assert applied.created == 1
    assert repeated.created == 0
    assert repeated.already_present == 1
    database.close()


def test_backfill_emits_legacy_fit_timestamps_as_aware_utc(tmp_path):
    database, workouts, events = temporary_repositories(tmp_path)
    fit_directory = tmp_path / "fits"
    fit_directory.mkdir()
    fit_path = fit_directory / "midnight.fit"
    fit_path.write_bytes(b"midnight")
    insert_workout(
        database,
        fit_path.name,
        datetime(2026, 8, 1, 22, 30),
    )

    HistoricalActivityFactBackfill(workouts, events, fit_directory).run(
        date(2026, 8, 1), date(2026, 8, 1), dry_run=False
    )
    identity = FitFileSourceIdentity().create(fit_path)
    event = events.get_by_source_identity(
        AthleteMemoryEventType.ACTIVITY_RECORDED,
        identity.provider,
        identity.external_id,
    )

    assert event is not None
    assert event.payload["activity"]["start"] == "2026-08-01T22:30:00+00:00"
    calendar = ActivityCalendarBuilder(events, EmptyPlanProvider()).build(
        date(2026, 8, 2), date(2026, 8, 2)
    )
    assert calendar.days[0].activities[0].activity_id == event.event_id
    database.close()


def test_standard_importer_projects_existing_analyzed_row_as_fact(tmp_path):
    database, _, events = temporary_repositories(tmp_path)
    fit_directory = tmp_path / "fits"
    fit_directory.mkdir()
    fit_path = fit_directory / "existing.fit"
    fit_path.write_bytes(b"existing")
    insert_workout(database, fit_path.name, datetime(2026, 8, 1, 8, 0))
    database.close()

    first = import_workouts(fit_directory, tmp_path / "activities.duckdb")
    second = import_workouts(fit_directory, tmp_path / "activities.duckdb")

    assert first == (0, 1, 0)
    assert second == (0, 0, 1)
    database = Database(tmp_path / "activities.duckdb")
    repository = AthleteMemoryRepository(database)
    identity = FitFileSourceIdentity().create(fit_path)
    event = repository.get_by_source_identity(
        AthleteMemoryEventType.ACTIVITY_RECORDED,
        identity.provider,
        identity.external_id,
    )
    assert event is not None
    assert event.event_type is AthleteMemoryEventType.ACTIVITY_RECORDED
    database.close()
