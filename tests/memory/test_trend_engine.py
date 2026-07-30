from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from athlete.memory.models import (
    AthleteMemorySnapshot,
    DateRange,
    WorkoutMemoryObservation,
)
from athlete.memory.trends import TrendEngine


def build_observation(
    event_id: str,
    *,
    planned_duration: float = 60,
    executed_duration: float = 55,
    planned_tss: float = 80,
    executed_tss: float = 75,
    completion_score: float = 90,
    execution_score: float = 88,
) -> WorkoutMemoryObservation:

    return WorkoutMemoryObservation(
        event_id=event_id,
        occurred_at=datetime(2026, 8, 1, 8, 0),
        planned_duration=planned_duration,
        executed_duration=executed_duration,
        planned_tss=planned_tss,
        executed_tss=executed_tss,
        completion_score=completion_score,
        execution_score=execution_score,
        feedback_status="completed",
        completed=True,
    )


def build_snapshot(
    observations: tuple[WorkoutMemoryObservation, ...],
) -> AthleteMemorySnapshot:

    start = datetime(2026, 8, 1, 0, 0)
    return AthleteMemorySnapshot(
        period=DateRange(start=start, end=start + timedelta(days=7)),
        workout_observations=observations,
        source_event_ids=tuple(observation.event_id for observation in observations),
        schema_version=1,
    )


def test_trend_engine_returns_zero_values_for_an_empty_snapshot():

    report = TrendEngine().analyze(build_snapshot(()))

    assert report.workouts_count == 0
    assert report.planned_duration == 0
    assert report.executed_duration == 0
    assert report.planned_tss == 0
    assert report.executed_tss == 0
    assert report.average_completion_score == 0.0
    assert report.average_execution_score == 0.0


def test_trend_engine_reports_a_single_workout():

    observation = build_observation("event-1")
    snapshot = build_snapshot((observation,))

    report = TrendEngine().analyze(snapshot)

    assert report.period == snapshot.period
    assert report.workouts_count == 1
    assert report.planned_duration == 60
    assert report.executed_duration == 55
    assert report.planned_tss == 80
    assert report.executed_tss == 75
    assert report.average_completion_score == 90
    assert report.average_execution_score == 88


def test_trend_engine_calculates_sums_and_averages_for_multiple_workouts():

    snapshot = build_snapshot(
        (
            build_observation(
                "event-1",
                planned_duration=60,
                executed_duration=50,
                planned_tss=80,
                executed_tss=70,
                completion_score=80,
                execution_score=70,
            ),
            build_observation(
                "event-2",
                planned_duration=90,
                executed_duration=90,
                planned_tss=120,
                executed_tss=120,
                completion_score=100,
                execution_score=90,
            ),
        )
    )

    report = TrendEngine().analyze(snapshot)

    assert report.workouts_count == 2
    assert report.planned_duration == 150
    assert report.executed_duration == 140
    assert report.planned_tss == 200
    assert report.executed_tss == 190
    assert report.average_completion_score == 90
    assert report.average_execution_score == 80


def test_trend_engine_preserves_zero_values_from_observations():

    snapshot = build_snapshot(
        (
            build_observation(
                "zero-workout",
                planned_duration=0,
                executed_duration=0,
                planned_tss=0,
                executed_tss=0,
                completion_score=0,
                execution_score=0,
            ),
        )
    )

    report = TrendEngine().analyze(snapshot)

    assert report.workouts_count == 1
    assert report.planned_duration == 0
    assert report.executed_duration == 0
    assert report.planned_tss == 0
    assert report.executed_tss == 0
    assert report.average_completion_score == 0
    assert report.average_execution_score == 0


def test_training_trend_report_is_immutable():

    report = TrendEngine().analyze(build_snapshot(()))

    with pytest.raises(FrozenInstanceError):
        report.workouts_count = 1


def test_trend_engine_is_deterministic_and_does_not_mutate_its_input():

    observations = (
        build_observation("event-1", completion_score=80),
        build_observation("event-2", completion_score=100),
    )
    snapshot = build_snapshot(observations)
    original_snapshot = snapshot
    original_observations = snapshot.workout_observations

    first_report = TrendEngine().analyze(snapshot)
    second_report = TrendEngine().analyze(snapshot)

    assert first_report == second_report
    assert snapshot is original_snapshot
    assert snapshot.workout_observations is original_observations
    assert snapshot.workout_observations == observations
