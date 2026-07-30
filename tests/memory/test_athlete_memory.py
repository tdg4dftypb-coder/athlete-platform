from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta

import duckdb
import pytest

from athlete.memory.history import AthleteMemoryHistoryAdapter
from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
)
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.serializer import WorkoutCompletedSerializer
from athlete.memory.writer import AthleteMemoryWriter
from core.database import Database
from execution.result import ExecutionResult
from feedback.models import WorkoutFeedback, WorkoutFeedbackStatus
from pipeline.models import PostWorkoutResult
from schema.athlete_memory_schema import AthleteMemorySchema
from training.activity import Activity, ActivityRecord
from training.analysis.workout_summary import WorkoutSummary
from workout.blocks import WorkoutBlock
from workout.models import Workout


def build_post_workout_result(
    *,
    start: datetime | None = None,
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
        completion_score=100,
        power_score=None,
        cadence_score=None,
        heart_rate_score=None,
        execution_score=100,
        completed=True,
        blocks=[],
        insights=["Workout completed"],
    )

    feedback = WorkoutFeedback(
        status=WorkoutFeedbackStatus.EXCELLENT,
        headline="Świetnie wykonany trening",
        summary="Plan został zrealizowany z bardzo wysoką jakością.",
        execution_score=100,
        completion_score=100,
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
    assert payload["workout"]["name"] == "Threshold Test"
    assert payload["activity"]["duration"] == 3600
    assert payload["workout_summary"]["tss"] == 80
    assert payload["execution"]["execution_score"] == 100
    assert payload["feedback"]["status"] == "excellent"
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


def test_repository_rejects_duplicate_source_key_without_replacing_event(tmp_path):

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

    with pytest.raises(duckdb.ConstraintException):
        repository.append(
            replace(
                event,
                event_id="event-2",
                payload={"workout": {"name": "Duplicate"}},
            )
        )

    assert repository.load_between(occurred_at, occurred_at) == [event]

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

    event = AthleteMemoryWriter(repository).write(result)
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


def test_history_adapter_receives_events_in_repository_order(tmp_path):

    db, repository = build_repository(tmp_path)
    writer = AthleteMemoryWriter(repository)
    earlier = build_post_workout_result(start=datetime(2026, 7, 30, 8, 0))
    later = build_post_workout_result(start=datetime(2026, 7, 31, 8, 0))

    writer.write(later)
    writer.write(earlier)

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
