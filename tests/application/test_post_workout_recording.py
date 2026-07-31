from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from application.post_workout_recording import (
    PostWorkoutRecordingResult,
    PostWorkoutRecordingService,
)
from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType, DateRange
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import (
    AthleteMemoryRepository,
    DuplicateSourceIdentityError,
)
from athlete.memory.writer import AthleteMemoryWriter
from core.database import Database
from execution.result import ExecutionResult
from feedback.models import WorkoutFeedback, WorkoutFeedbackStatus
from pipeline.models import PostWorkoutResult
from pipeline.post_workout import PostWorkoutPipeline
from schema.athlete_memory_schema import AthleteMemorySchema
from training.activity import Activity, ActivityRecord
from training.ingestion.source_identity import SourceIdentity
from training.analysis.workout_summary import WorkoutSummary
from workout.blocks import WorkoutBlock
from workout.models import Workout


def build_workout() -> Workout:

    return Workout(
        name="Threshold Test",
        goal="FTP development",
        description="",
        duration=5,
        target_tss=10,
        target_if=0.95,
        blocks=[
            WorkoutBlock(
                name="Threshold",
                description="",
                duration=300,
                power_from=250,
                power_to=280,
                cadence_from=85,
                cadence_to=95,
                repeat=1,
            )
        ],
    )


def build_activity(start: datetime | None = None) -> Activity:

    start = start or datetime(2026, 8, 1, 8, 0)
    return Activity(
        start=start,
        end=start + timedelta(seconds=300),
        sport="cycling",
        distance=5,
        calories=150,
        duration=300,
        records=[
            ActivityRecord(
                timestamp=start,
                elapsed_time=0,
                power=260,
                heart_rate=150,
                cadence=90,
                speed=35,
            ),
            ActivityRecord(
                timestamp=start + timedelta(seconds=299),
                elapsed_time=299,
                power=270,
                heart_rate=160,
                cadence=91,
                speed=35,
            ),
        ],
    )


def build_post_workout_result(
    workout: Workout,
    activity: Activity,
) -> PostWorkoutResult:

    summary = WorkoutSummary(
        start=activity.start,
        end=activity.end,
        sport=activity.sport,
        duration=activity.duration,
        distance=activity.distance,
        calories=activity.calories,
        average_power=265,
        normalized_power=265,
        max_power=270,
        intensity_factor=0.93,
        tss=10,
        average_hr=155,
        max_hr=160,
        average_cadence=90.5,
        max_cadence=91,
    )
    execution = ExecutionResult(
        planned_duration=5,
        executed_duration=5,
        planned_tss=10,
        executed_tss=10,
        completion_score=100,
        power_score=None,
        cadence_score=None,
        heart_rate_score=None,
        execution_score=100,
        completed=True,
        blocks=[],
        insights=[],
    )
    feedback = WorkoutFeedback(
        status=WorkoutFeedbackStatus.EXCELLENT,
        headline="Excellent",
        summary="Completed.",
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


def build_event() -> AthleteMemoryEvent:

    return AthleteMemoryEvent(
        event_id="event-1",
        occurred_at=datetime(2026, 8, 1, 8, 5),
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key="activity-1",
        schema_version=1,
        payload={},
    )


def build_source_identity() -> SourceIdentity:
    return SourceIdentity(provider="activity", external_id="activity-1")


def test_recording_service_passes_exact_inputs_and_results_between_components():

    workout = build_workout()
    activity = build_activity()
    post_workout = build_post_workout_result(workout, activity)
    event = build_event()
    source_identity = build_source_identity()
    pipeline = Mock()
    writer = Mock()
    pipeline.run.return_value = post_workout
    writer.write.return_value = event

    result = PostWorkoutRecordingService(pipeline, writer).record(
        workout,
        activity,
        source_identity,
    )

    pipeline.run.assert_called_once_with(workout, activity)
    writer.write.assert_called_once_with(post_workout, source_identity)
    assert result.post_workout is post_workout
    assert result.event is event


def test_recording_service_propagates_pipeline_error_without_calling_writer():

    pipeline = Mock()
    writer = Mock()
    pipeline.run.side_effect = RuntimeError("pipeline failed")

    with pytest.raises(RuntimeError, match="pipeline failed"):
        PostWorkoutRecordingService(pipeline, writer).record(
            build_workout(),
            build_activity(),
            build_source_identity(),
        )

    writer.write.assert_not_called()


def test_recording_service_propagates_writer_error():

    workout = build_workout()
    activity = build_activity()
    pipeline = Mock()
    writer = Mock()
    pipeline.run.return_value = build_post_workout_result(workout, activity)
    writer.write.side_effect = RuntimeError("write failed")

    with pytest.raises(RuntimeError, match="write failed"):
        PostWorkoutRecordingService(pipeline, writer).record(
            workout,
            activity,
            build_source_identity(),
        )

    pipeline.run.assert_called_once_with(workout, activity)
    writer.write.assert_called_once_with(
        pipeline.run.return_value,
        build_source_identity(),
    )


def test_post_workout_recording_result_is_immutable():

    result = PostWorkoutRecordingResult(
        post_workout=build_post_workout_result(build_workout(), build_activity()),
        event=build_event(),
    )

    with pytest.raises(FrozenInstanceError):
        result.event = build_event()


def test_recording_service_persists_and_reader_projects_event(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    workout = build_workout()
    activity = build_activity()
    source_identity = build_source_identity()

    result = PostWorkoutRecordingService(
        PostWorkoutPipeline(),
        AthleteMemoryWriter(repository),
    ).record(workout, activity, source_identity)
    snapshot = AthleteMemoryReader(repository).read(
        DateRange(
            start=activity.start,
            end=activity.end + timedelta(seconds=1),
        )
    )

    assert result.event.event_type == AthleteMemoryEventType.WORKOUT_COMPLETED
    assert len(snapshot.workout_observations) == 1
    assert snapshot.source_event_ids == (result.event.event_id,)

    db.close()


def test_activity_does_not_receive_source_identity():

    assert not hasattr(build_activity(), "source_identity")


def test_recording_service_rejects_a_duplicate_source_identity(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    service = PostWorkoutRecordingService(
        PostWorkoutPipeline(),
        AthleteMemoryWriter(repository),
    )
    workout = build_workout()
    activity = build_activity()
    source_identity = build_source_identity()

    service.record(workout, activity, source_identity)

    with pytest.raises(DuplicateSourceIdentityError):
        service.record(workout, activity, source_identity)

    db.close()
