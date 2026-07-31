from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from application.weekly_review import WeeklyReviewWorkflow
from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
    AthleteMemorySnapshot,
    DateRange,
    PatternReport,
    TrainingTrendReport,
    WorkoutMemoryObservation,
)
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.trends import TrendEngine
from athlete.memory.patterns import PatternDetector
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.writer import AthleteMemoryWriter
from athlete.review.models import ReviewPeriodMismatchError, WeeklyTrainingReview
from athlete.review.weekly import WeeklyReviewService
from core.database import Database
from schema.athlete_memory_schema import AthleteMemorySchema


def build_period() -> DateRange:

    start = datetime(2026, 8, 1)
    return DateRange(start=start, end=start + timedelta(days=7))


def build_snapshot(period: DateRange) -> AthleteMemorySnapshot:

    observation = WorkoutMemoryObservation(
        event_id="event-1",
        occurred_at=period.start + timedelta(hours=1),
        planned_duration=60,
        executed_duration=55,
        planned_tss=80,
        executed_tss=75,
        completion_score=90.0,
        execution_score=88.0,
        feedback_status="completed",
        completed=True,
    )
    return AthleteMemorySnapshot(
        period=period,
        workout_observations=(observation,),
        source_event_ids=(observation.event_id,),
        schema_version=1,
    )


def build_trends(period: DateRange) -> TrainingTrendReport:

    return TrainingTrendReport(
        period=period,
        workouts_count=1,
        planned_duration=60,
        executed_duration=55,
        planned_tss=80,
        executed_tss=75,
        average_completion_score=90.0,
        average_execution_score=88.0,
    )


def build_patterns(period: DateRange) -> PatternReport:

    return PatternReport(period=period, patterns=(), source_event_ids=("event-1",))


def build_review(period: DateRange) -> WeeklyTrainingReview:

    trends = build_trends(period)
    patterns = build_patterns(period)
    return WeeklyTrainingReview(
        period=period,
        trends=trends,
        patterns=patterns,
        source_event_ids=patterns.source_event_ids,
    )


def test_weekly_review_workflow_orchestrates_existing_components():

    period = build_period()
    snapshot = build_snapshot(period)
    trends = build_trends(period)
    patterns = build_patterns(period)
    review = build_review(period)
    reader = Mock()
    trend_engine = Mock()
    pattern_detector = Mock()
    review_service = Mock()
    reader.read.return_value = snapshot
    trend_engine.analyze.return_value = trends
    pattern_detector.analyze.return_value = patterns
    review_service.build.return_value = review

    result = WeeklyReviewWorkflow(
        reader,
        trend_engine,
        pattern_detector,
        review_service,
    ).run(period)

    reader.read.assert_called_once_with(period)
    trend_engine.analyze.assert_called_once_with(snapshot)
    pattern_detector.analyze.assert_called_once_with(snapshot)
    review_service.build.assert_called_once_with(trends, patterns)
    assert result is review


def test_weekly_review_workflow_returns_the_snapshot_used_for_the_review():
    period = build_period()
    snapshot = build_snapshot(period)
    review = build_review(period)
    reader = Mock()
    trend_engine = Mock()
    pattern_detector = Mock()
    review_service = Mock()
    reader.read.return_value = snapshot
    trend_engine.analyze.return_value = review.trends
    pattern_detector.analyze.return_value = review.patterns
    review_service.build.return_value = review
    workflow = WeeklyReviewWorkflow(
        reader,
        trend_engine,
        pattern_detector,
        review_service,
    )

    result_snapshot, result_review = workflow.run_with_snapshot(period)

    reader.read.assert_called_once_with(period)
    assert result_snapshot is snapshot
    assert result_review is review


@pytest.mark.parametrize(
    ("component_name", "error"),
    [
        ("reader", RuntimeError("reader failed")),
        ("trend_engine", RuntimeError("trend failed")),
        ("pattern_detector", RuntimeError("pattern failed")),
        (
            "review_service",
            ReviewPeriodMismatchError("periods differ"),
        ),
    ],
)
def test_weekly_review_workflow_propagates_component_errors(component_name, error):

    period = build_period()
    snapshot = build_snapshot(period)
    reader = Mock()
    trend_engine = Mock()
    pattern_detector = Mock()
    review_service = Mock()
    reader.read.return_value = snapshot
    trend_engine.analyze.return_value = build_trends(period)
    pattern_detector.analyze.return_value = build_patterns(period)
    getattr(
        {
            "reader": reader.read,
            "trend_engine": trend_engine.analyze,
            "pattern_detector": pattern_detector.analyze,
            "review_service": review_service.build,
        },
        "get"
    )(component_name).side_effect = error

    with pytest.raises(type(error), match=str(error)):
        WeeklyReviewWorkflow(
            reader,
            trend_engine,
            pattern_detector,
            review_service,
        ).run(period)


def build_event(event_id: str, occurred_at: datetime) -> AthleteMemoryEvent:

    return AthleteMemoryEvent(
        event_id=event_id,
        occurred_at=occurred_at,
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key=f"activity-{event_id}",
        schema_version=1,
        payload={
            "schema_version": 1,
            "execution": {
                "planned_duration": 60,
                "executed_duration": 60,
                "planned_tss": 100,
                "executed_tss": 100,
                "completion_score": 95.0,
                "execution_score": 95.0,
                "completed": True,
            },
            "feedback": {"status": "completed"},
        },
    )


def build_real_workflow(repository: AthleteMemoryRepository) -> WeeklyReviewWorkflow:

    return WeeklyReviewWorkflow(
        AthleteMemoryReader(repository),
        TrendEngine(),
        PatternDetector(),
        WeeklyReviewService(),
    )


def test_weekly_review_workflow_returns_empty_review_for_empty_memory(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    period = build_period()

    review = build_real_workflow(AthleteMemoryRepository(db)).run(period)

    assert review.period == period
    assert review.trends.workouts_count == 0
    assert review.patterns.patterns == ()
    assert review.source_event_ids == ()

    db.close()


def test_weekly_review_workflow_uses_only_events_inside_the_period(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    period = build_period()
    in_first = build_event("in-first", period.start + timedelta(hours=1))
    in_second = build_event("in-second", period.start + timedelta(days=1))
    at_end = build_event("at-end", period.end)
    before_start = build_event("before-start", period.start - timedelta(seconds=1))

    for event in (at_end, in_second, before_start, in_first):
        repository.append(event)

    review = build_real_workflow(repository).run(period)

    assert review.trends.workouts_count == 2
    assert review.trends.planned_tss == 200
    assert review.source_event_ids == ("in-first", "in-second")
    assert review.trends.period == period
    assert review.patterns.period == period
    assert review.period == period

    db.close()
