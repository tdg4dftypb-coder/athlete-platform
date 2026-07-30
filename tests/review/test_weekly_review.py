from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from athlete.memory.models import (
    DateRange,
    PatternReport,
    TrainingPattern,
    TrainingTrendReport,
)
from athlete.review import (
    ReviewPeriodMismatchError,
    WeeklyReviewService,
    WeeklyTrainingReview,
)


def build_period(*, start: datetime | None = None) -> DateRange:

    start = start or datetime(2026, 8, 3)
    return DateRange(start=start, end=start + timedelta(days=7))


def build_trends(period: DateRange) -> TrainingTrendReport:

    return TrainingTrendReport(
        period=period,
        workouts_count=3,
        planned_duration=180,
        executed_duration=170,
        planned_tss=220,
        executed_tss=210,
        average_completion_score=0.90,
        average_execution_score=0.88,
    )


def build_patterns(
    period: DateRange,
    *,
    patterns: tuple[TrainingPattern, ...] = (),
    source_event_ids: tuple[str, ...] = ("event-1", "event-2", "event-3"),
) -> PatternReport:

    return PatternReport(
        period=period,
        patterns=patterns,
        source_event_ids=source_event_ids,
    )


def test_weekly_review_composes_existing_reports_without_modification():

    period = build_period()
    trends = build_trends(period)
    patterns = build_patterns(period)

    review = WeeklyReviewService().build(trends, patterns)

    assert review.period == period
    assert review.trends is trends
    assert review.patterns is patterns
    assert review.source_event_ids is patterns.source_event_ids
    assert review.source_event_ids == patterns.source_event_ids


def test_weekly_review_preserves_an_empty_pattern_report():

    period = build_period()
    patterns = build_patterns(period)

    review = WeeklyReviewService().build(build_trends(period), patterns)

    assert review.patterns.patterns == ()
    assert review.source_event_ids == ("event-1", "event-2", "event-3")


def test_weekly_review_preserves_pattern_order_and_source_event_ids_exactly():

    period = build_period()
    first_pattern = TrainingPattern(
        code="FIRST",
        severity="INFO",
        description="First detected behavior.",
        source_event_ids=("event-2",),
    )
    second_pattern = TrainingPattern(
        code="SECOND",
        severity="WARNING",
        description="Second detected behavior.",
        source_event_ids=("event-1", "event-3"),
    )
    source_event_ids = ("event-3", "event-1", "event-3", "event-2")
    patterns = build_patterns(
        period,
        patterns=(first_pattern, second_pattern),
        source_event_ids=source_event_ids,
    )

    review = WeeklyReviewService().build(build_trends(period), patterns)

    assert review.patterns.patterns == (first_pattern, second_pattern)
    assert review.source_event_ids == source_event_ids


def test_weekly_review_rejects_reports_for_different_periods():

    trends = build_trends(build_period())
    patterns = build_patterns(
        build_period(start=datetime(2026, 8, 10)),
    )

    with pytest.raises(ReviewPeriodMismatchError) as error:
        WeeklyReviewService().build(trends, patterns)

    assert repr(trends.period) in str(error.value)
    assert repr(patterns.period) in str(error.value)


def test_weekly_training_review_is_immutable():

    period = build_period()
    review = WeeklyReviewService().build(
        build_trends(period),
        build_patterns(period),
    )

    with pytest.raises(FrozenInstanceError):
        review.source_event_ids = ()


def test_weekly_review_is_deterministic_and_does_not_mutate_inputs():

    period = build_period()
    trends = build_trends(period)
    patterns = build_patterns(period)
    original_trends = trends
    original_patterns = patterns

    first_review = WeeklyReviewService().build(trends, patterns)
    second_review = WeeklyReviewService().build(trends, patterns)

    assert first_review == second_review
    assert trends is original_trends
    assert patterns is original_patterns


def test_athlete_review_public_imports_are_available():

    assert WeeklyTrainingReview.__name__ == "WeeklyTrainingReview"
    assert WeeklyReviewService.__name__ == "WeeklyReviewService"
    assert issubclass(ReviewPeriodMismatchError, ValueError)
