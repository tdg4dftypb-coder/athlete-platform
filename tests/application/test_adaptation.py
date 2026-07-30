from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from inspect import signature

import pytest

from application import (
    AdaptationDirective,
    AdaptationPolicy,
    AdaptationStatus,
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


def build_assessment(
    status: AthleteAssessmentStatus,
    reasons: tuple[AthleteAssessmentReason, ...] = (),
) -> AthleteAssessment:

    return AthleteAssessment(
        as_of=datetime(2026, 8, 7, 12, 0),
        status=status,
        training_assessment=TrainingAssessment(
            as_of=datetime(2026, 8, 7, 12, 0),
            period=None,
            status=TrainingAssessmentStatus.NO_CLEAR_PATTERN,
            supporting_patterns=(),
        ),
        reasons=reasons,
    )


def test_adaptation_directive_is_frozen():

    directive = AdaptationDirective(
        as_of=datetime(2026, 8, 7, 12, 0),
        status=AdaptationStatus.MAINTAIN,
        source_reasons=(),
    )

    with pytest.raises(FrozenInstanceError):
        directive.status = AdaptationStatus.REDUCE_LOAD


def test_policy_has_no_constructor_dependencies():

    assert tuple(signature(AdaptationPolicy).parameters) == ()


def test_insufficient_data_preserves_reasons_and_as_of():

    assessment = build_assessment(
        AthleteAssessmentStatus.INSUFFICIENT_DATA,
        (
            AthleteAssessmentReason.MISSING_ATHLETE_STATE,
            AthleteAssessmentReason.NO_TRAINING_DATA,
        ),
    )

    directive = AdaptationPolicy().evaluate(assessment)

    assert directive.status is AdaptationStatus.INSUFFICIENT_DATA
    assert directive.as_of is assessment.as_of
    assert directive.source_reasons is assessment.reasons


def test_caution_maps_to_reduce_load_and_preserves_reason_order():

    assessment = build_assessment(
        AthleteAssessmentStatus.CAUTION,
        (
            AthleteAssessmentReason.LOW_RECOVERY,
            AthleteAssessmentReason.HIGH_FATIGUE,
            AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED,
        ),
    )

    directive = AdaptationPolicy().evaluate(assessment)

    assert directive.status is AdaptationStatus.REDUCE_LOAD
    assert directive.source_reasons is assessment.reasons
    assert directive.source_reasons == (
        AthleteAssessmentReason.LOW_RECOVERY,
        AthleteAssessmentReason.HIGH_FATIGUE,
        AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED,
    )


def test_stable_maps_to_maintain_without_reasons():

    assessment = build_assessment(
        AthleteAssessmentStatus.STABLE,
        (AthleteAssessmentReason.LOW_RECOVERY,),
    )

    directive = AdaptationPolicy().evaluate(assessment)

    assert directive.status is AdaptationStatus.MAINTAIN
    assert directive.source_reasons == ()


def test_policy_is_deterministic_and_does_not_mutate_assessment():

    assessment = build_assessment(
        AthleteAssessmentStatus.CAUTION,
        (AthleteAssessmentReason.HIGH_FATIGUE,),
    )
    original_reasons = assessment.reasons

    first = AdaptationPolicy().evaluate(assessment)
    second = AdaptationPolicy().evaluate(assessment)

    assert first == second
    assert assessment.reasons is original_reasons
    assert assessment.status is AthleteAssessmentStatus.CAUTION


def test_public_application_exports_are_available():

    assert AdaptationDirective.__name__ == "AdaptationDirective"
    assert AdaptationPolicy.__name__ == "AdaptationPolicy"
    assert AdaptationStatus.__name__ == "AdaptationStatus"


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


def build_assessment_from_memory(
    repository: AthleteMemoryRepository,
    athlete,
):

    review = build_workflow(repository).run(build_period())
    context = AthleteKnowledgeContextBuilder().build(
        as_of=datetime(2026, 8, 7, 12, 0),
        athlete_state=athlete,
        weekly_review=review,
    )
    training = TrainingAssessmentBuilder().build(context)

    return AthleteAssessmentBuilder().build(context, training)


def test_integration_empty_memory_maps_to_insufficient_data(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()

    assessment = build_assessment_from_memory(
        AthleteMemoryRepository(db),
        build_athlete(),
    )
    directive = AdaptationPolicy().evaluate(assessment)

    assert assessment.status is AthleteAssessmentStatus.INSUFFICIENT_DATA
    assert directive.status is AdaptationStatus.INSUFFICIENT_DATA

    db.close()


def test_integration_stable_maps_to_maintain(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    repository.append(build_event(build_period()))

    assessment = build_assessment_from_memory(
        repository,
        build_athlete(recovery_score=70, fatigue=79),
    )
    directive = AdaptationPolicy().evaluate(assessment)

    assert assessment.status is AthleteAssessmentStatus.STABLE
    assert directive.status is AdaptationStatus.MAINTAIN

    db.close()


def test_integration_caution_maps_to_reduce_load(tmp_path):

    db = Database(tmp_path / "athlete_memory.duckdb")
    AthleteMemorySchema(db).create()
    repository = AthleteMemoryRepository(db)
    repository.append(build_event(build_period()))

    assessment = build_assessment_from_memory(
        repository,
        build_athlete(recovery_score=69, fatigue=79),
    )
    directive = AdaptationPolicy().evaluate(assessment)

    assert assessment.status is AthleteAssessmentStatus.CAUTION
    assert directive.status is AdaptationStatus.REDUCE_LOAD

    db.close()
