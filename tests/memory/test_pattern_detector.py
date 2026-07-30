from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from athlete.memory.models import (
    AthleteMemorySnapshot,
    DateRange,
    TrainingPattern,
    WorkoutMemoryObservation,
)
from athlete.memory.patterns import PatternDetector


def build_observation(
    event_id: str,
    *,
    completion_score: float = 95.0,
    execution_score: float = 95.0,
    planned_tss: float = 100,
    executed_tss: float = 100,
) -> WorkoutMemoryObservation:

    return WorkoutMemoryObservation(
        event_id=event_id,
        occurred_at=datetime(2026, 8, 1, 8, 0),
        planned_duration=60,
        executed_duration=60,
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

    start = datetime(2026, 8, 1)
    return AthleteMemorySnapshot(
        period=DateRange(start=start, end=start + timedelta(days=7)),
        workout_observations=observations,
        source_event_ids=tuple(observation.event_id for observation in observations),
        schema_version=1,
    )


def pattern_by_code(report, code: str) -> TrainingPattern:

    return next(pattern for pattern in report.patterns if pattern.code == code)


def test_empty_snapshot_returns_an_empty_pattern_report():

    snapshot = build_snapshot(())

    report = PatternDetector().analyze(snapshot)

    assert report.period == snapshot.period
    assert report.patterns == ()
    assert report.source_event_ids == ()


def test_too_few_workouts_do_not_create_patterns():

    snapshot = build_snapshot(
        (
            build_observation("event-1"),
            build_observation("event-2"),
        )
    )

    assert PatternDetector().analyze(snapshot).patterns == ()


def test_detector_finds_consistent_execution_with_all_evidence_events():

    snapshot = build_snapshot(
        (
            build_observation("event-1"),
            build_observation("event-2", completion_score=90.0),
            build_observation(
                "event-3",
                completion_score=100.0,
                execution_score=90.0,
            ),
        )
    )

    report = PatternDetector().analyze(snapshot)
    pattern = pattern_by_code(report, "CONSISTENT_EXECUTION")

    assert pattern.severity == "INFO"
    assert pattern.source_event_ids == ("event-1", "event-2", "event-3")


def test_detector_does_not_find_consistent_execution_with_one_weaker_workout():

    snapshot = build_snapshot(
        (
            build_observation("event-1"),
            build_observation("event-2"),
            build_observation("event-3", execution_score=89.0),
        )
    )

    assert "CONSISTENT_EXECUTION" not in {
        pattern.code
        for pattern in PatternDetector().analyze(snapshot).patterns
    }


def test_detector_does_not_interpret_a_fractional_score_as_90_percent():

    snapshot = build_snapshot(
        (
            build_observation(
                "event-1",
                completion_score=0.90,
                execution_score=0.90,
            ),
            build_observation(
                "event-2",
                completion_score=0.90,
                execution_score=0.90,
            ),
            build_observation(
                "event-3",
                completion_score=0.90,
                execution_score=0.90,
            ),
        )
    )

    assert "CONSISTENT_EXECUTION" not in {
        pattern.code
        for pattern in PatternDetector().analyze(snapshot).patterns
    }


def test_detector_finds_repeated_partial_execution_and_excludes_boundaries():

    snapshot = build_snapshot(
        (
            build_observation("zero", completion_score=0),
            build_observation("lower", completion_score=79.0),
            build_observation("upper", completion_score=80.0),
            build_observation("fraction", completion_score=0.90),
            build_observation("another", completion_score=50.0),
            build_observation("consistent-boundary", completion_score=90.0),
        )
    )

    pattern = pattern_by_code(
        PatternDetector().analyze(snapshot),
        "REPEATED_PARTIAL_EXECUTION",
    )

    assert pattern.severity == "WARNING"
    assert pattern.source_event_ids == ("lower", "fraction", "another")


def test_report_keeps_all_analyzed_events_while_pattern_keeps_only_evidence():

    snapshot = build_snapshot(
        (
            build_observation("partial-1", completion_score=50.0),
            build_observation("partial-2", completion_score=60.0),
            build_observation("neutral", completion_score=85.0),
        )
    )

    report = PatternDetector().analyze(snapshot)
    pattern = pattern_by_code(report, "REPEATED_PARTIAL_EXECUTION")

    assert report.source_event_ids == ("partial-1", "partial-2", "neutral")
    assert pattern.source_event_ids == ("partial-1", "partial-2")


def test_detector_finds_repeated_under_execution_and_excludes_85_percent_boundary():

    snapshot = build_snapshot(
        (
            build_observation("under-1", executed_tss=84.99),
            build_observation("at-boundary", executed_tss=85),
            build_observation("under-2", executed_tss=80),
        )
    )

    pattern = pattern_by_code(
        PatternDetector().analyze(snapshot),
        "REPEATED_UNDER_EXECUTION",
    )

    assert pattern.source_event_ids == ("under-1", "under-2")


def test_detector_ignores_non_positive_planned_tss_for_under_execution():

    snapshot = build_snapshot(
        (
            build_observation("under", planned_tss=100, executed_tss=80),
            build_observation("zero", planned_tss=0, executed_tss=200),
            build_observation("negative", planned_tss=-10, executed_tss=0),
        )
    )

    pattern_codes = {
        pattern.code
        for pattern in PatternDetector().analyze(snapshot).patterns
    }
    assert "REPEATED_UNDER_EXECUTION" not in pattern_codes
    assert "REPEATED_OVER_EXECUTION" not in pattern_codes


def test_detector_finds_repeated_over_execution_and_excludes_115_percent_boundary():

    snapshot = build_snapshot(
        (
            build_observation("over-1", executed_tss=115.01),
            build_observation("at-boundary", executed_tss=115),
            build_observation("over-2", executed_tss=120),
        )
    )

    pattern = pattern_by_code(
        PatternDetector().analyze(snapshot),
        "REPEATED_OVER_EXECUTION",
    )

    assert pattern.source_event_ids == ("over-1", "over-2")


def test_detector_returns_multiple_patterns_in_a_stable_order():

    snapshot = build_snapshot(
        (
            build_observation("partial-under-1", completion_score=50.0, executed_tss=80),
            build_observation("partial-under-2", completion_score=60.0, executed_tss=70),
            build_observation("over-1", executed_tss=120),
            build_observation("over-2", executed_tss=130),
        )
    )

    report = PatternDetector().analyze(snapshot)

    assert [pattern.code for pattern in report.patterns] == [
        "REPEATED_PARTIAL_EXECUTION",
        "REPEATED_UNDER_EXECUTION",
        "REPEATED_OVER_EXECUTION",
    ]
    assert report.source_event_ids == (
        "partial-under-1",
        "partial-under-2",
        "over-1",
        "over-2",
    )


def test_pattern_models_are_immutable():

    pattern = TrainingPattern(
        code="CONSISTENT_EXECUTION",
        severity="INFO",
        description="Stable execution.",
        source_event_ids=("event-1",),
    )
    report = PatternDetector().analyze(build_snapshot(()))

    with pytest.raises(FrozenInstanceError):
        pattern.code = "OTHER"
    with pytest.raises(FrozenInstanceError):
        report.patterns = ()


def test_detector_is_deterministic_and_does_not_mutate_snapshot():

    observations = (
        build_observation("event-1", completion_score=50.0),
        build_observation("event-2", completion_score=60.0),
    )
    snapshot = build_snapshot(observations)
    original_observations = snapshot.workout_observations

    first_report = PatternDetector().analyze(snapshot)
    second_report = PatternDetector().analyze(snapshot)

    assert first_report == second_report
    assert snapshot.workout_observations is original_observations
    assert snapshot.workout_observations == observations
