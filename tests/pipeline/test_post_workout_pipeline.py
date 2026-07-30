from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from unittest.mock import Mock, call

import pytest

from execution.context import ExecutionContext
from execution.result import ExecutionResult
from feedback.models import WorkoutFeedback, WorkoutFeedbackStatus
from pipeline.models import PostWorkoutResult
from pipeline.post_workout import PostWorkoutPipeline
from timeline.models import WorkoutTimeline
from training.activity import Activity, ActivityRecord
from training.analysis.workout_analyzer import WorkoutAnalyzer
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
                duration=300,
                power_from=250,
                power_to=280,
                cadence_from=85,
                cadence_to=95,
                repeat=1,
                description="",
            )
        ],
    )


def build_activity() -> Activity:

    start = datetime(2026, 7, 30, 8, 0)

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


def build_summary() -> WorkoutSummary:

    start = datetime(2026, 7, 30, 8, 0)

    return WorkoutSummary(
        start=start,
        end=start + timedelta(seconds=300),
        sport="cycling",
        duration=300,
        distance=5,
        calories=150,
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


def build_execution() -> ExecutionResult:

    return ExecutionResult(
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


def build_feedback() -> WorkoutFeedback:

    return WorkoutFeedback(
        status=WorkoutFeedbackStatus.EXCELLENT,
        headline="Świetnie wykonany trening",
        summary="Plan został zrealizowany z bardzo wysoką jakością.",
        execution_score=100,
        completion_score=100,
        positive_signals=(),
        attention_signals=(),
    )


def test_pipeline_orchestrates_components_in_order():

    workout = build_workout()
    activity = build_activity()
    summary = build_summary()
    timeline = WorkoutTimeline(blocks=[], total_duration=300)
    execution = build_execution()
    feedback = build_feedback()

    analyzer = Mock()
    timeline_builder = Mock()
    execution_engine = Mock()
    feedback_engine = Mock()

    analyzer.analyze.return_value = summary
    timeline_builder.build.return_value = timeline
    execution_engine.analyze_context.return_value = execution
    feedback_engine.build.return_value = feedback

    components = Mock()
    components.attach_mock(analyzer, "analyzer")
    components.attach_mock(timeline_builder, "timeline_builder")
    components.attach_mock(execution_engine, "execution_engine")
    components.attach_mock(feedback_engine, "feedback_engine")

    result = PostWorkoutPipeline(
        workout_analyzer=analyzer,
        timeline_builder=timeline_builder,
        execution_engine=execution_engine,
        feedback_engine=feedback_engine,
    ).run(workout, activity)

    context = ExecutionContext(
        workout=workout,
        activity=activity,
        summary=summary,
        timeline=timeline,
    )

    assert components.mock_calls == [
        call.analyzer.analyze(activity),
        call.timeline_builder.build(workout),
        call.execution_engine.analyze_context(context),
        call.feedback_engine.build(execution),
    ]
    assert result == PostWorkoutResult(
        workout=workout,
        activity=activity,
        workout_summary=summary,
        execution=execution,
        feedback=feedback,
    )


def test_pipeline_does_not_modify_workout_or_activity():

    workout = build_workout()
    activity = build_activity()

    original_workout = deepcopy(workout)
    original_activity = deepcopy(activity)

    analyzer = Mock()
    timeline_builder = Mock()
    execution_engine = Mock()
    feedback_engine = Mock()

    analyzer.analyze.return_value = build_summary()
    timeline_builder.build.return_value = WorkoutTimeline(
        blocks=[],
        total_duration=300,
    )
    execution_engine.analyze_context.return_value = build_execution()
    feedback_engine.build.return_value = build_feedback()

    PostWorkoutPipeline(
        workout_analyzer=analyzer,
        timeline_builder=timeline_builder,
        execution_engine=execution_engine,
        feedback_engine=feedback_engine,
    ).run(workout, activity)

    assert workout == original_workout
    assert activity == original_activity


def test_post_workout_result_is_immutable():

    result = PostWorkoutResult(
        workout=build_workout(),
        activity=build_activity(),
        workout_summary=build_summary(),
        execution=build_execution(),
        feedback=build_feedback(),
    )

    with pytest.raises(FrozenInstanceError):
        result.execution = build_execution()


def test_pipeline_runs_end_to_end_with_real_components():

    workout = build_workout()
    activity = build_activity()

    result = PostWorkoutPipeline().run(workout, activity)

    assert isinstance(result.workout_summary, WorkoutSummary)
    assert isinstance(result.execution, ExecutionResult)
    assert isinstance(result.feedback, WorkoutFeedback)
    assert result.workout is workout
    assert result.activity is activity
