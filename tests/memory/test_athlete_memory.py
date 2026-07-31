from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta

import duckdb
import pytest

from athlete.memory.history import AthleteMemoryHistoryAdapter
from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
    DateRange,
)
from athlete.memory.patterns import PatternDetector
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import (
    AthleteMemoryRepository,
    DuplicateSourceIdentityError,
)
from athlete.memory.serializer import WorkoutCompletedSerializer
from athlete.memory.writer import AthleteMemoryWriter
from core.database import Database
from execution.result import ExecutionResult
from feedback.models import WorkoutFeedback, WorkoutFeedbackStatus
from pipeline.models import PostWorkoutResult
from schema.athlete_memory_schema import AthleteMemorySchema
from training.activity import Activity, ActivityRecord
from training.ingestion.source_identity import SourceIdentity
from training.analysis.workout_summary import WorkoutSummary
from workout.blocks import WorkoutBlock
from workout.models import Workout


def build_post_workout_result(
    *,
    start: datetime | None = None,
    completion_score: float = 100.0,
    execution_score: float = 100.0,
) -> PostWorkoutResult:

    start = start or datetime(2026, 7, 30, 8, 0)

    workout = Workout(
        name="Threshold Test",
        goal="FTP development",
        description="",
        duration=60,
        target_tss=80,
        target_if=0.95,
        blocks=[
            WorkoutBlock(
                name="Threshold",
                description="FTP effort.",
                duration=3600,
                power_from=0.95,
                power_to=1.0,
                cadence_from=85,
                cadence_to=95,
            )
        ],
    )

    activity = Activity(
        start=start,
        end=start + timedelta(minutes=60),
        sport="cycling",
        distance=35.0,
        calories=800,
        duration=3600,
        records=[
            ActivityRecord(
                timestamp=start,
                elapsed_time=0,
                power=250,
                heart_rate=150,
                cadence=90,
                speed=35,
            )
        ],
    )

    summary = WorkoutSummary(
        start=activity.start,
        end=activity.end,
        sport=activity.sport,
        duration=activity.duration,
        distance=activity.distance,
        calories=activity.calories,
        average_power=250,
        normalized_power=260,
        max_power=500,
        intensity_factor=0.91,
        tss=80,
        average_hr=150,
        max_hr=170,
        average_cadence=90,
        max_cadence=110,
    )

    execution = ExecutionResult(
        planned_duration=60,
        executed_duration=60,
        planned_tss=80,
        executed_tss=80,
        completion_score=completion_score,
        power_score=None,
        cadence_score=None,
        heart_rate_score=None,
        execution_score=execution_score,
        completed=True,
        blocks=[],
        insights=["Workout completed"],
    )

    feedback = WorkoutFeedback(
        status=WorkoutFeedbackStatus.EXCELLENT,
        headline="Świetnie wykonany trening",
        summary="Plan został zrealizowany z bardzo wysoką jakością.",
        execution_score=execution_score,
        completion_score=completion_score,
        positive_signals=(),
        attention_signals=(),
    )

    return PostWorkoutResult(
        workout=workout,
        activity=activity,
        workout_summary=summary,
        execution=execution,
        feedback=feedback,
    )


def build_repository(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()

    return db, AthleteMemoryRepository(db)


def legacy_source_identity(result: PostWorkoutResult) -> SourceIdentity:
    return SourceIdentity(
        provider="activity",
        external_id=result.activity.start.isoformat(),
    )


def test_memory_event_is_immutable():

    event = AthleteMemoryEvent(
        event_id="event-1",
        occurred_at=datetime(2026, 7, 30, 9, 0),
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key="2026-07-30T08:00:00",
        schema_version=1,
        payload={},
    )

    with pytest.raises(FrozenInstanceError):
        event.event_id = "event-2"


def test_workout_completed_serializer_uses_post_workout_snapshot():

    result = build_post_workout_result()

    payload = WorkoutCompletedSerializer().serialize(result)

    assert payload["schema_version"] == 1
    assert payload["analysis_version"] == WorkoutCompletedSerializer.ANALYSIS_VERSION
    assert payload["feedback_version"] == WorkoutCompletedSerializer.FEEDBACK_VERSION
    assert isinstance(payload["analysis_version"], str)
    assert isinstance(payload["feedback_version"], str)
    assert payload["workout"]["name"] == "Threshold Test"
    assert payload["activity"]["duration"] == 3600
    assert payload["workout_summary"]["tss"] == 80
    assert payload["execution"]["execution_score"] == 100
    assert payload["feedback"]["status"] == "excellent"
    assert "records" not in payload["activity"]


def test_workout_completed_serializer_preserves_v1_sections_units_and_plan_snapshot():

    result = build_post_workout_result()

    payload = WorkoutCompletedSerializer().serialize(result)

    assert {"activity", "workout", "workout_summary", "execution", "feedback"} <= set(
        payload
    )
    assert payload["activity"]["duration"] == result.activity.duration == 3600
    assert result.workout_summary.duration == 3600
    assert payload["execution"]["planned_duration"] == 60
    assert payload["execution"]["executed_duration"] == 60
    assert payload["workout"]["goal"] == result.workout.goal
    assert payload["workout"]["target_tss"] == result.workout.target_tss
    assert payload["workout"]["target_if"] == result.workout.target_if
    assert payload["workout"]["blocks"] == [
        {
            "name": "Threshold",
            "description": "FTP effort.",
            "duration": 3600,
            "power_from": 0.95,
            "power_to": 1.0,
            "cadence_from": 85,
            "cadence_to": 95,
            "repeat": 1,
        }
    ]
    assert "records" not in payload["activity"]


def test_repository_appends_and_loads_events_between_dates(tmp_path):

    db, repository = build_repository(tmp_path)
    occurred_at = datetime(2026, 7, 30, 9, 0)

    event = AthleteMemoryEvent(
        event_id="event-1",
        occurred_at=occurred_at,
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key="activity-1",
        schema_version=1,
        payload={"workout": {"name": "Threshold Test"}},
    )

    repository.append(event)

    events = repository.load_between(
        occurred_at - timedelta(minutes=1),
        occurred_at + timedelta(minutes=1),
    )

    assert events == [event]

    db.close()


def test_schema_initialization_is_idempotent(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    schema = AthleteMemorySchema(db)

    schema.create()
    schema.create()

    table = db.connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'athlete_memory_events'
        """
    ).fetchone()

    assert table == ("athlete_memory_events",)

    db.close()


def test_repository_rejects_duplicate_source_identity_without_replacing_event(tmp_path):

    db, repository = build_repository(tmp_path)
    occurred_at = datetime(2026, 7, 30, 9, 0)
    event = AthleteMemoryEvent(
        event_id="event-1",
        occurred_at=occurred_at,
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key="activity-1",
        schema_version=1,
        payload={"workout": {"name": "Original"}},
    )

    repository.append(event)

    with pytest.raises(DuplicateSourceIdentityError):
        repository.append(
            replace(
                event,
                event_id="event-2",
                payload={"workout": {"name": "Duplicate"}},
            )
        )

    assert repository.load_between(occurred_at, occurred_at) == [event]

    db.close()


def test_repository_does_not_map_an_unrelated_constraint_failure_to_duplicate_identity():

    class ConstraintFailingConnection:
        def execute(self, query, parameters):
            raise duckdb.ConstraintException(
                'Constraint Error: Duplicate key "event_id: event-1" violates primary key constraint.'
            )

    database = type(
        "ConstraintFailingDatabase",
        (),
        {"connection": ConstraintFailingConnection()},
    )()
    event = AthleteMemoryEvent(
        event_id="event-1",
        occurred_at=datetime(2026, 7, 30, 9, 0),
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="fit_file",
        source_key="sha256:abc",
        schema_version=1,
        payload={},
    )

    with pytest.raises(duckdb.ConstraintException):
        AthleteMemoryRepository(database).append(event)


def test_repository_allows_the_same_source_key_for_different_source_types(tmp_path):

    db, repository = build_repository(tmp_path)
    occurred_at = datetime(2026, 7, 30, 9, 0)
    legacy_event = AthleteMemoryEvent(
        event_id="legacy-event",
        occurred_at=occurred_at,
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key="shared-key",
        schema_version=1,
        payload={"workout": {"name": "Legacy"}},
    )
    fit_event = replace(
        legacy_event,
        event_id="fit-event",
        source_type="fit_file",
        payload={"workout": {"name": "FIT"}},
    )

    repository.append(legacy_event)
    repository.append(fit_event)

    assert repository.load_between(occurred_at, occurred_at) == [legacy_event, fit_event]

    db.close()


def test_schema_migrates_legacy_source_key_index_without_losing_events(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    db.connection.execute(
        """
        CREATE TABLE athlete_memory_events (
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
    db.connection.execute(
        """
        CREATE UNIQUE INDEX athlete_memory_events_source_key_unique
        ON athlete_memory_events (source_key)
        """
    )
    db.connection.execute(
        """
        INSERT INTO athlete_memory_events
        (event_id, occurred_at, event_type, source_type, source_key, schema_version, payload_json)
        VALUES ('legacy-event', '2026-07-30 09:00:00', 'workout_completed', 'activity', 'legacy-key', 1, '{}')
        """
    )

    schema = AthleteMemorySchema(db)
    schema.create()
    schema.create()
    repository = AthleteMemoryRepository(db)
    occurred_at = datetime(2026, 7, 30, 9, 0)

    assert repository.load_between(occurred_at, occurred_at)[0].event_id == "legacy-event"
    repository.append(
        AthleteMemoryEvent(
            event_id="fit-event",
            occurred_at=occurred_at,
            event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
            source_type="fit_file",
            source_key="legacy-key",
            schema_version=1,
            payload={},
        )
    )
    with pytest.raises(DuplicateSourceIdentityError):
        repository.append(
            AthleteMemoryEvent(
                event_id="duplicate-fit-event",
                occurred_at=occurred_at,
                event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
                source_type="fit_file",
                source_key="legacy-key",
                schema_version=1,
                payload={},
            )
        )

    index_names = {
        row[0]
        for row in db.connection.execute(
            "SELECT index_name FROM duckdb_indexes()"
        ).fetchall()
    }
    assert "athlete_memory_events_source_key_unique" not in index_names
    assert "athlete_memory_events_source_identity_unique" in index_names

    db.close()


def test_schema_rolls_back_the_legacy_index_when_new_index_creation_fails(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    db.connection.execute(
        """
        CREATE TABLE athlete_memory_events (
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
    db.connection.execute(
        """
        CREATE UNIQUE INDEX athlete_memory_events_source_key_unique
        ON athlete_memory_events (source_key)
        """
    )
    db.connection.execute(
        """
        INSERT INTO athlete_memory_events
        (event_id, occurred_at, event_type, source_type, source_key, schema_version, payload_json)
        VALUES ('legacy-event', '2026-07-30 09:00:00', 'workout_completed', 'activity', 'legacy-key', 1, '{}')
        """
    )

    class FailingConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, query):
            if "CREATE UNIQUE INDEX IF NOT EXISTS" in query:
                raise RuntimeError("new source index failed")
            return self.connection.execute(query)

    failing_database = type("FailingDatabase", (), {"connection": FailingConnection(db.connection)})()

    with pytest.raises(RuntimeError, match="new source index failed"):
        AthleteMemorySchema(failing_database).create()

    assert db.connection.execute(
        "SELECT source_key FROM athlete_memory_events"
    ).fetchall() == [("legacy-key",)]
    index_names = {
        row[0]
        for row in db.connection.execute(
            "SELECT index_name FROM duckdb_indexes()"
        ).fetchall()
    }
    assert "athlete_memory_events_source_key_unique" in index_names
    assert "athlete_memory_events_source_identity_unique" not in index_names

    db.close()


def test_load_between_is_inclusive_and_returns_events_chronologically(tmp_path):

    db, repository = build_repository(tmp_path)
    start = datetime(2026, 7, 30, 9, 0)
    middle = start + timedelta(minutes=30)
    end = start + timedelta(minutes=60)
    events = [
        AthleteMemoryEvent(
            event_id=f"event-{index}",
            occurred_at=occurred_at,
            event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
            source_type="activity",
            source_key=f"activity-{index}",
            schema_version=1,
            payload={"workout": {"name": f"Workout {index}"}},
        )
        for index, occurred_at in enumerate((start, middle, end), start=1)
    ]

    for event in reversed(events):
        repository.append(event)

    assert repository.load_between(start, end) == events

    db.close()


def test_writer_persists_workout_completed_and_builds_history(tmp_path):

    db, repository = build_repository(tmp_path)
    result = build_post_workout_result()

    event = AthleteMemoryWriter(repository).write(
        result,
        legacy_source_identity(result),
    )
    events = repository.load_between(
        result.activity.start,
        result.activity.end,
    )

    history = AthleteMemoryHistoryAdapter().build(events)

    assert events == [event]
    assert event.event_type == AthleteMemoryEventType.WORKOUT_COMPLETED
    assert event.source_key == result.activity.start.isoformat()
    assert history.count == 1
    assert history.events[0].title == "Threshold Test"
    assert history.events[0].payload == event.payload

    db.close()


def test_writer_preserves_workout_completed_v1_envelope_contract(tmp_path):

    db, repository = build_repository(tmp_path)
    result = build_post_workout_result()

    source_identity = SourceIdentity(
        provider="fit_file",
        external_id="sha256:abc",
    )

    event = AthleteMemoryWriter(repository).write(result, source_identity)

    assert event.event_type is AthleteMemoryEventType.WORKOUT_COMPLETED
    assert event.source_type == source_identity.provider
    assert event.source_key == source_identity.external_id
    assert event.schema_version == WorkoutCompletedSerializer.SCHEMA_VERSION
    assert event.occurred_at == result.activity.end

    db.close()


def test_workout_completed_round_trip_preserves_observation_semantics(tmp_path):

    db, repository = build_repository(tmp_path)
    result = build_post_workout_result(
        completion_score=92.5,
        execution_score=88.0,
    )

    event = AthleteMemoryWriter(repository).write(
        result,
        legacy_source_identity(result),
    )
    snapshot = AthleteMemoryReader(repository).read(
        DateRange(
            start=result.activity.start,
            end=result.activity.end + timedelta(microseconds=1),
        )
    )

    assert snapshot.source_event_ids == (event.event_id,)
    observation = snapshot.workout_observations[0]
    assert observation.event_id == event.event_id
    assert observation.occurred_at == result.activity.end
    assert observation.planned_duration == result.execution.planned_duration
    assert observation.executed_duration == result.execution.executed_duration
    assert observation.planned_tss == result.execution.planned_tss
    assert observation.executed_tss == result.execution.executed_tss
    assert observation.completion_score == result.execution.completion_score
    assert observation.execution_score == result.execution.execution_score
    assert observation.feedback_status == result.feedback.status.value
    assert observation.completed is result.execution.completed

    db.close()


def test_reader_projects_mixed_legacy_and_fit_source_history(tmp_path):

    db, repository = build_repository(tmp_path)
    writer = AthleteMemoryWriter(repository)
    legacy_result = build_post_workout_result(start=datetime(2026, 7, 30, 8, 0))
    fit_result = build_post_workout_result(start=datetime(2026, 7, 31, 8, 0))

    legacy_event = writer.write(
        legacy_result,
        legacy_source_identity(legacy_result),
    )
    fit_identity = SourceIdentity(
        provider="fit_file",
        external_id=f"sha256:{'a' * 64}",
    )
    fit_event = writer.write(fit_result, fit_identity)

    snapshot = AthleteMemoryReader(repository).read(
        DateRange(
            start=legacy_result.activity.start,
            end=fit_result.activity.end + timedelta(microseconds=1),
        )
    )

    assert [event.source_type for event in repository.load_between(
        legacy_result.activity.start,
        fit_result.activity.end,
    )] == ["activity", "fit_file"]
    assert snapshot.source_event_ids == (legacy_event.event_id, fit_event.event_id)
    assert [observation.event_id for observation in snapshot.workout_observations] == [
        legacy_event.event_id,
        fit_event.event_id,
    ]
    assert [observation.executed_tss for observation in snapshot.workout_observations] == [
        legacy_result.execution.executed_tss,
        fit_result.execution.executed_tss,
    ]

    db.close()


def test_memory_round_trip_preserves_percent_scores_for_consistent_execution(tmp_path):

    db, repository = build_repository(tmp_path)
    writer = AthleteMemoryWriter(repository)
    start = datetime(2026, 7, 30, 8, 0)

    for day in range(3):
        result = build_post_workout_result(
            start=start + timedelta(days=day),
            completion_score=90.0,
            execution_score=90.0,
        )
        writer.write(result, legacy_source_identity(result))

    period = DateRange(
        start=start,
        end=start + timedelta(days=3, minutes=1),
    )
    snapshot = AthleteMemoryReader(repository).read(period)
    report = PatternDetector().analyze(snapshot)

    assert [
        observation.completion_score
        for observation in snapshot.workout_observations
    ] == [90.0, 90.0, 90.0]
    assert [
        observation.execution_score
        for observation in snapshot.workout_observations
    ] == [90.0, 90.0, 90.0]
    assert "CONSISTENT_EXECUTION" in {
        pattern.code
        for pattern in report.patterns
    }

    db.close()


def test_memory_round_trip_does_not_interpret_0_90_as_90_percent(tmp_path):

    db, repository = build_repository(tmp_path)
    writer = AthleteMemoryWriter(repository)
    start = datetime(2026, 7, 30, 8, 0)

    for day in range(3):
        result = build_post_workout_result(
            start=start + timedelta(days=day),
            completion_score=0.90,
            execution_score=0.90,
        )
        writer.write(result, legacy_source_identity(result))

    period = DateRange(
        start=start,
        end=start + timedelta(days=3, minutes=1),
    )
    snapshot = AthleteMemoryReader(repository).read(period)
    report = PatternDetector().analyze(snapshot)

    assert [
        observation.execution_score
        for observation in snapshot.workout_observations
    ] == [0.90, 0.90, 0.90]
    assert "CONSISTENT_EXECUTION" not in {
        pattern.code
        for pattern in report.patterns
    }

    db.close()


def test_history_adapter_receives_events_in_repository_order(tmp_path):

    db, repository = build_repository(tmp_path)
    writer = AthleteMemoryWriter(repository)
    earlier = build_post_workout_result(start=datetime(2026, 7, 30, 8, 0))
    later = build_post_workout_result(start=datetime(2026, 7, 31, 8, 0))

    writer.write(later, legacy_source_identity(later))
    writer.write(earlier, legacy_source_identity(earlier))

    events = repository.load_between(
        earlier.activity.start,
        later.activity.end,
    )
    history = AthleteMemoryHistoryAdapter().build(events)

    assert [event.occurred_at for event in events] == [
        earlier.activity.end,
        later.activity.end,
    ]
    assert [event.timestamp for event in history.events] == [
        later.activity.end,
        earlier.activity.end,
    ]

    db.close()
