from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from inspect import signature

import pytest

from application import (
    AthleteKnowledgeContext,
    AthleteKnowledgeContextBuilder,
    TrainingAssessment,
    TrainingAssessmentBuilder,
    TrainingAssessmentStatus,
)
from application.weekly_review import WeeklyReviewWorkflow
from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
    DateRange,
    PatternReport,
    TrainingPattern,
    TrainingTrendReport,
)
from athlete.memory.patterns import PatternDetector
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.trends import TrendEngine
from athlete.review.models import WeeklyTrainingReview
from athlete.review.weekly import WeeklyReviewService
from core.database import Database
from schema.athlete_memory_schema import AthleteMemorySchema


def build_period() -> DateRange:

    start = datetime(2026, 8, 1)
    return DateRange(start=start, end=start + timedelta(days=7))


def build_pattern(code: str) -> TrainingPattern:

    return TrainingPattern(
        code=code,
        severity="WARNING" if code.startswith("REPEATED_") else "INFO",
        description=f"{code} observed.",
        source_event_ids=(f"{code}-event",),
    )


def build_review(
    *,
    workouts_count: int = 1,
    patterns: tuple[TrainingPattern, ...] = (),
) -> WeeklyTrainingReview:

    period = build_period()
    trends = TrainingTrendReport(
        period=period,
        workouts_count=workouts_count,
        planned_duration=60.0,
        executed_duration=60.0,
        planned_tss=80.0,
        executed_tss=80.0,
        average_completion_score=100.0,
        average_execution_score=100.0,
    )
    pattern_report = PatternReport(
        period=period,
        patterns=patterns,
        source_event_ids=tuple(
            event_id
            for pattern in patterns
            for event_id in pattern.source_event_ids
        ),
    )
    return WeeklyTrainingReview(
        period=period,
        trends=trends,
        patterns=pattern_report,
        source_event_ids=pattern_report.source_event_ids,
    )


def build_context(
    weekly_review: WeeklyTrainingReview | None,
) -> tuple[datetime, AthleteKnowledgeContext]:

    as_of = datetime(2026, 8, 7, 12, 0)
    context = AthleteKnowledgeContextBuilder().build(
        as_of=as_of,
        weekly_review=weekly_review,
    )
    return as_of, context


def test_training_assessment_model_is_frozen():

    assessment = TrainingAssessment(
        as_of=datetime(2026, 8, 7, 12, 0),
        period=None,
        status=TrainingAssessmentStatus.NO_TRAINING_DATA,
        supporting_patterns=(),
    )

    with pytest.raises(FrozenInstanceError):
        assessment.status = TrainingAssessmentStatus.NO_CLEAR_PATTERN


def test_missing_weekly_review_means_no_training_data():

    as_of, context = build_context(None)

    assessment = TrainingAssessmentBuilder().build(context)

    assert assessment.as_of is as_of
    assert assessment.period is None
    assert assessment.status is TrainingAssessmentStatus.NO_TRAINING_DATA
    assert assessment.supporting_patterns == ()


def test_empty_review_means_no_training_data_and_preserves_period():

    review = build_review(workouts_count=0)
    _, context = build_context(review)

    assessment = TrainingAssessmentBuilder().build(context)

    assert assessment.status is TrainingAssessmentStatus.NO_TRAINING_DATA
    assert assessment.period is review.period
    assert assessment.supporting_patterns == ()


@pytest.mark.parametrize(
    "warning_code",
    (
        "REPEATED_PARTIAL_EXECUTION",
        "REPEATED_UNDER_EXECUTION",
        "REPEATED_OVER_EXECUTION",
    ),
)
def test_warning_patterns_require_attention(warning_code: str):

    warning = build_pattern(warning_code)
    _, context = build_context(build_review(patterns=(warning,)))

    assessment = TrainingAssessmentBuilder().build(context)

    assert assessment.status is TrainingAssessmentStatus.ATTENTION_REQUIRED
    assert assessment.supporting_patterns == (warning,)
    assert assessment.supporting_patterns[0] is warning


def test_warning_patterns_take_precedence_and_keep_only_warnings_in_order():

    consistent = build_pattern("CONSISTENT_EXECUTION")
    partial = build_pattern("REPEATED_PARTIAL_EXECUTION")
    unknown = build_pattern("UNUSED_PATTERN")
    over = build_pattern("REPEATED_OVER_EXECUTION")
    review = build_review(patterns=(consistent, partial, unknown, over))
    _, context = build_context(review)

    assessment = TrainingAssessmentBuilder().build(context)

    assert assessment.status is TrainingAssessmentStatus.ATTENTION_REQUIRED
    assert assessment.supporting_patterns == (partial, over)
    assert assessment.supporting_patterns[0] is partial
    assert assessment.supporting_patterns[1] is over


def test_consistent_execution_is_used_when_no_warning_pattern_exists():

    consistent = build_pattern("CONSISTENT_EXECUTION")
    _, context = build_context(build_review(patterns=(consistent,)))

    assessment = TrainingAssessmentBuilder().build(context)

    assert assessment.status is TrainingAssessmentStatus.CONSISTENT_EXECUTION
    assert assessment.supporting_patterns == (consistent,)
    assert assessment.supporting_patterns[0] is consistent


def test_nonempty_review_without_a_supported_pattern_is_not_interpreted():

    unknown = build_pattern("UNUSED_PATTERN")
    _, context = build_context(build_review(patterns=(unknown,)))

    assessment = TrainingAssessmentBuilder().build(context)

    assert assessment.status is TrainingAssessmentStatus.NO_CLEAR_PATTERN
    assert assessment.supporting_patterns == ()


def test_builder_is_deterministic_and_does_not_mutate_context_or_review():

    warning = build_pattern("REPEATED_UNDER_EXECUTION")
    review = build_review(patterns=(warning,))
    as_of, context = build_context(review)
    original_patterns = review.patterns.patterns

    first = TrainingAssessmentBuilder().build(context)
    second = TrainingAssessmentBuilder().build(context)

    assert first == second
    assert first.as_of is as_of
    assert context.weekly_review is review
    assert review.patterns.patterns is original_patterns
    assert review.patterns.patterns == (warning,)


def test_builder_has_no_constructor_dependencies():

    assert tuple(signature(TrainingAssessmentBuilder).parameters) == ()


def build_workflow(repository: AthleteMemoryRepository) -> WeeklyReviewWorkflow:

    return WeeklyReviewWorkflow(
        AthleteMemoryReader(repository),
        TrendEngine(),
        PatternDetector(),
        WeeklyReviewService(),
    )


def build_completed_event(
    period: DateRange,
) -> AthleteMemoryEvent:

    return AthleteMemoryEvent(
        event_id="event-1",
        occurred_at=period.start + timedelta(hours=1),
        event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
        source_type="activity",
        source_key="activity-1",
        schema_version=1,
        payload={
            "schema_version": 1,
            "execution": {
                "planned_duration": 60,
                "executed_duration": 60,
                "planned_tss": 80,
                "executed_tss": 80,
                "completion_score": 100.0,
                "execution_score": 100.0,
                "completed": True,
            },
            "feedback": {"status": "completed"},
        },
    )


def test_assessment_integration_handles_empty_memory(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    period = build_period()
    review = build_workflow(AthleteMemoryRepository(db)).run(period)
    _, context = build_context(review)

    assessment = TrainingAssessmentBuilder().build(context)

    assert assessment.status is TrainingAssessmentStatus.NO_TRAINING_DATA
    assert assessment.period is period

    db.close()


def test_assessment_integration_handles_single_event_without_pattern(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    period = build_period()
    repository.append(build_completed_event(period))
    review = build_workflow(repository).run(period)
    _, context = build_context(review)

    assessment = TrainingAssessmentBuilder().build(context)

    assert review.trends.workouts_count == 1
    assert review.patterns.patterns == ()
    assert assessment.status is TrainingAssessmentStatus.NO_CLEAR_PATTERN
    assert assessment.period is period

    db.close()
