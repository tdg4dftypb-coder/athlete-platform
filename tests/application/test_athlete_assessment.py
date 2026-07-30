from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from inspect import signature

import pytest

from application import (
    AthleteAssessment,
    AthleteAssessmentBuilder,
    AthleteAssessmentReason,
    AthleteAssessmentStatus,
    AthleteKnowledgeContextBuilder,
    TrainingAssessment,
    TrainingAssessmentBuilder,
    TrainingAssessmentStatus,
)
from application.weekly_review import WeeklyReviewWorkflow
from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType, DateRange
from athlete.memory.patterns import PatternDetector
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.trends import TrendEngine
from athlete.review.weekly import WeeklyReviewService
from core.database import Database
from schema.athlete_memory_schema import AthleteMemorySchema
from tests.helpers import build_athlete


def build_training(
    status: TrainingAssessmentStatus = TrainingAssessmentStatus.NO_CLEAR_PATTERN,
) -> TrainingAssessment:

    return TrainingAssessment(
        as_of=datetime(2026, 8, 7, 12, 0),
        period=None,
        status=status,
        supporting_patterns=(),
    )


def build_context(*, athlete_state=None):

    return AthleteKnowledgeContextBuilder().build(
        as_of=datetime(2026, 8, 7, 12, 0),
        athlete_state=athlete_state,
    )


def test_athlete_assessment_model_is_frozen():

    assessment = AthleteAssessment(
        as_of=datetime(2026, 8, 7, 12, 0),
        status=AthleteAssessmentStatus.STABLE,
        training_assessment=build_training(),
        reasons=(),
    )

    with pytest.raises(FrozenInstanceError):
        assessment.status = AthleteAssessmentStatus.CAUTION


def test_builder_has_no_constructor_dependencies():

    assert tuple(signature(AthleteAssessmentBuilder).parameters) == ()


def test_missing_athlete_state_means_insufficient_data():

    training = build_training()
    context = build_context()

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.INSUFFICIENT_DATA
    assert assessment.reasons == (
        AthleteAssessmentReason.MISSING_ATHLETE_STATE,
    )


def test_no_training_data_means_insufficient_data():

    training = build_training(TrainingAssessmentStatus.NO_TRAINING_DATA)
    context = build_context(athlete_state=build_athlete())

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.INSUFFICIENT_DATA
    assert assessment.reasons == (AthleteAssessmentReason.NO_TRAINING_DATA,)


def test_insufficient_data_has_precedence_over_caution_conditions():

    training = build_training(TrainingAssessmentStatus.NO_TRAINING_DATA)
    context = build_context(
        athlete_state=build_athlete(recovery_score=69, fatigue=80),
    )

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.INSUFFICIENT_DATA
    assert assessment.reasons == (AthleteAssessmentReason.NO_TRAINING_DATA,)


def test_insufficient_data_collects_reasons_in_order_and_has_precedence():

    training = build_training(TrainingAssessmentStatus.NO_TRAINING_DATA)
    context = build_context()

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.INSUFFICIENT_DATA
    assert assessment.reasons == (
        AthleteAssessmentReason.MISSING_ATHLETE_STATE,
        AthleteAssessmentReason.NO_TRAINING_DATA,
    )


def test_low_recovery_requires_caution():

    training = build_training()
    context = build_context(athlete_state=build_athlete(recovery_score=69))

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.CAUTION
    assert assessment.reasons == (AthleteAssessmentReason.LOW_RECOVERY,)


def test_recovery_score_70_does_not_require_caution():

    training = build_training()
    context = build_context(athlete_state=build_athlete(recovery_score=70))

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.STABLE
    assert assessment.reasons == ()


def test_high_fatigue_requires_caution():

    training = build_training()
    context = build_context(athlete_state=build_athlete(fatigue=80))

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.CAUTION
    assert assessment.reasons == (AthleteAssessmentReason.HIGH_FATIGUE,)


def test_fatigue_79_does_not_require_caution():

    training = build_training()
    context = build_context(athlete_state=build_athlete(fatigue=79))

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.STABLE
    assert assessment.reasons == ()


def test_training_attention_requires_caution():

    training = build_training(TrainingAssessmentStatus.ATTENTION_REQUIRED)
    context = build_context(athlete_state=build_athlete())

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.CAUTION
    assert assessment.reasons == (
        AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED,
    )


@pytest.mark.parametrize(
    "training_status",
    (
        TrainingAssessmentStatus.CONSISTENT_EXECUTION,
        TrainingAssessmentStatus.NO_CLEAR_PATTERN,
    ),
)
def test_non_attention_training_statuses_are_stable(training_status):

    training = build_training(training_status)
    context = build_context(athlete_state=build_athlete(recovery_score=70, fatigue=79))

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.STABLE
    assert assessment.reasons == ()


def test_caution_collects_reasons_in_the_defined_order():

    training = build_training(TrainingAssessmentStatus.ATTENTION_REQUIRED)
    context = build_context(
        athlete_state=build_athlete(recovery_score=69, fatigue=80),
    )

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.CAUTION
    assert assessment.reasons == (
        AthleteAssessmentReason.LOW_RECOVERY,
        AthleteAssessmentReason.HIGH_FATIGUE,
        AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED,
    )


def test_low_recovery_and_high_fatigue_both_remain_visible():

    training = build_training()
    context = build_context(
        athlete_state=build_athlete(recovery_score=69, fatigue=80),
    )

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.CAUTION
    assert assessment.reasons == (
        AthleteAssessmentReason.LOW_RECOVERY,
        AthleteAssessmentReason.HIGH_FATIGUE,
    )


def test_consistent_training_does_not_hide_low_recovery():

    training = build_training(TrainingAssessmentStatus.CONSISTENT_EXECUTION)
    context = build_context(athlete_state=build_athlete(recovery_score=69))

    assessment = AthleteAssessmentBuilder().build(context, training)

    assert assessment.status is AthleteAssessmentStatus.CAUTION
    assert assessment.reasons == (AthleteAssessmentReason.LOW_RECOVERY,)


def test_builder_preserves_references_is_deterministic_and_does_not_mutate_inputs():

    athlete = build_athlete(recovery_score=69, fatigue=80)
    training = build_training(TrainingAssessmentStatus.ATTENTION_REQUIRED)
    context = build_context(athlete_state=athlete)
    original_recovery = athlete.recovery.score
    original_fatigue = athlete.performance.fatigue

    first = AthleteAssessmentBuilder().build(context, training)
    second = AthleteAssessmentBuilder().build(context, training)

    assert first == second
    assert first.as_of is context.as_of
    assert first.training_assessment is training
    assert context.athlete_state is athlete
    assert athlete.recovery.score == original_recovery
    assert athlete.performance.fatigue == original_fatigue


def build_period() -> DateRange:

    start = datetime(2026, 8, 1)
    return DateRange(start=start, end=start + timedelta(days=7))


def build_workflow(repository: AthleteMemoryRepository) -> WeeklyReviewWorkflow:

    return WeeklyReviewWorkflow(
        AthleteMemoryReader(repository),
        TrendEngine(),
        PatternDetector(),
        WeeklyReviewService(),
    )


def build_event(period: DateRange) -> AthleteMemoryEvent:

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


def test_assessment_integration_for_empty_memory(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    review = build_workflow(AthleteMemoryRepository(db)).run(build_period())
    context = AthleteKnowledgeContextBuilder().build(
        as_of=datetime(2026, 8, 7, 12, 0),
        athlete_state=build_athlete(),
        weekly_review=review,
    )

    training = TrainingAssessmentBuilder().build(context)
    assessment = AthleteAssessmentBuilder().build(context, training)

    assert training.status is TrainingAssessmentStatus.NO_TRAINING_DATA
    assert assessment.status is AthleteAssessmentStatus.INSUFFICIENT_DATA
    assert assessment.reasons == (AthleteAssessmentReason.NO_TRAINING_DATA,)

    db.close()


def test_assessment_integration_for_single_event_without_pattern(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    period = build_period()
    repository.append(build_event(period))
    review = build_workflow(repository).run(period)
    context = AthleteKnowledgeContextBuilder().build(
        as_of=datetime(2026, 8, 7, 12, 0),
        athlete_state=build_athlete(recovery_score=70, fatigue=79),
        weekly_review=review,
    )

    training = TrainingAssessmentBuilder().build(context)
    assessment = AthleteAssessmentBuilder().build(context, training)

    assert training.status is TrainingAssessmentStatus.NO_CLEAR_PATTERN
    assert assessment.status is AthleteAssessmentStatus.STABLE
    assert assessment.reasons == ()

    db.close()
