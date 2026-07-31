from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from application import (
    AdaptationDirective,
    AdaptationStatus,
    ExplainabilityResult,
    IntelligenceDecisionWorkflow,
    build_default_recommendation_engine,
)
from athlete.intelligence.models import (
    AthleteInsightType,
    AthleteObservationType,
    HealthObservationInput,
)
from decision.prescription.models import DecisionReason, TrainingObjective
from recommendation import (
    HydrationRecommendationRule,
    MobilityRecommendationRule,
    RecommendationResult,
    RecommendationType,
    RecoveryRecommendationRule,
    SleepRecommendationRule,
)
from workout.enums import WorkoutType

from tests.helpers import build_athlete


def test_workflow_connects_health_observations_to_insight_decision_and_explainability():
    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=80)
    health = HealthObservationInput(
        observed_at=datetime(2026, 7, 1, 8),
        hrv_delta_percent=-5.0,
        sleep_duration_minutes=360.0,
        sleep_baseline_minutes=420.0,
        recovery_score=90.0,
        evidence=("health-day-1",),
    )

    result = IntelligenceDecisionWorkflow().run(athlete, health=health)

    assert [observation.type for observation in result.observations] == [
        AthleteObservationType.HRV_BELOW_BASELINE,
        AthleteObservationType.SLEEP_DEBT,
        AthleteObservationType.RECOVERY_GOOD,
    ]
    assert [insight.type for insight in result.insights] == [
        AthleteInsightType.NEED_MORE_RECOVERY,
    ]
    assert result.plan.recommendation is WorkoutType.RECOVERY
    assert result.decision.objective is TrainingObjective.RECOVERY
    assert result.decision.decision_reasons == (
        DecisionReason.INSIGHT_NEED_MORE_RECOVERY,
    )
    assert result.explainability.contributing_factors == (
        "Recovery requirements detected.",
    )
    assert tuple(
        recommendation.type
        for recommendation in result.recommendations.recommendations
    ) == (
        RecommendationType.EXTEND_SLEEP,
        RecommendationType.APPLY_RECOVERY_PROTOCOL,
        RecommendationType.INCREASE_HYDRATION,
        RecommendationType.PERFORM_MOBILITY,
    )
    assert result.explainability.recommendations == (
        "Extend sleep duration.",
        "Apply recovery protocol.",
        "Increase hydration.",
        "Perform mobility work.",
    )


def test_workflow_is_deterministic_side_effect_free_and_result_is_immutable():
    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=80)
    health = HealthObservationInput(
        observed_at=datetime(2026, 7, 1, 8),
        hrv_delta_percent=-5.0,
        sleep_duration_minutes=360.0,
        sleep_baseline_minutes=420.0,
        recovery_score=None,
        evidence=("health-day-1",),
    )
    workflow = IntelligenceDecisionWorkflow()
    original_recovery = athlete.recovery.score

    result = workflow.run(athlete, health=health)

    assert workflow.run(athlete, health=health) == result
    assert athlete.recovery.score == original_recovery
    with pytest.raises(FrozenInstanceError):
        result.insights = ()
    with pytest.raises(FrozenInstanceError):
        result.recommendations = RecommendationResult((), None)


class SpyRecommendationEngine:
    def __init__(self, result: RecommendationResult) -> None:
        self.result = result
        self.contexts = []
        self.snapshots = []

    def evaluate(self, context):
        self.contexts.append(context)
        self.snapshots.append(deepcopy(context))
        return self.result


class SpyExplainabilityBuilder:
    def __init__(self) -> None:
        self.calls = []

    def build(self, decision_reasons, recommendations):
        self.calls.append((decision_reasons, recommendations))
        return ExplainabilityResult("summary", (), ())


def test_workflow_passes_exact_pipeline_outputs_through_recommendation_stage():
    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=80)
    health = HealthObservationInput(
        observed_at=datetime(2026, 7, 1, 8),
        hrv_delta_percent=-5.0,
        sleep_duration_minutes=360.0,
        sleep_baseline_minutes=420.0,
        recovery_score=None,
        evidence=("health-day-1",),
    )
    expected_recommendations = RecommendationResult((), None)
    recommendation_engine = SpyRecommendationEngine(expected_recommendations)
    explainability_builder = SpyExplainabilityBuilder()

    result = IntelligenceDecisionWorkflow(
        recommendation_engine=recommendation_engine,
        explainability_builder=explainability_builder,
    ).run(athlete, health=health)

    assert len(recommendation_engine.contexts) == 1
    context = recommendation_engine.contexts[0]
    assert context.decision is result.decision
    assert context.insights is result.insights
    assert context.observations is result.observations
    assert result.recommendations is expected_recommendations
    assert explainability_builder.calls == [
        (result.decision.decision_reasons, expected_recommendations)
    ]
    assert context == recommendation_engine.snapshots[0]


def test_workflow_supports_an_empty_recommendation_result():
    expected = RecommendationResult((), None)

    result = IntelligenceDecisionWorkflow(
        recommendation_engine=SpyRecommendationEngine(expected),
    ).run(build_athlete())

    assert result.recommendations is expected
    assert result.explainability.recommendations == ()


def test_default_composition_contains_the_four_recommendation_rules():
    engine = build_default_recommendation_engine()

    assert tuple(type(rule) for rule in engine._rules) == (
        SleepRecommendationRule,
        HydrationRecommendationRule,
        RecoveryRecommendationRule,
        MobilityRecommendationRule,
    )


def test_workflow_dates_recovery_recommendation_from_load_reduction_input():
    athlete = build_athlete(recovery_score=60, fatigue=20, freshness=20)
    as_of = datetime(2026, 7, 31, 8)
    adaptation = AdaptationDirective(
        as_of=as_of,
        status=AdaptationStatus.REDUCE_LOAD,
        source_reasons=(),
    )
    health = HealthObservationInput(
        observed_at=as_of,
        hrv_delta_percent=0.0,
        sleep_duration_minutes=480.0,
        sleep_baseline_minutes=480.0,
        recovery_score=60.0,
        evidence=("health-day",),
    )

    result = IntelligenceDecisionWorkflow().run(
        athlete,
        health=health,
        adaptation=adaptation,
    )

    assert result.recommendations.as_of == as_of
    assert tuple(
        recommendation.type
        for recommendation in result.recommendations.recommendations
    ) == (RecommendationType.APPLY_RECOVERY_PROTOCOL,)


def test_application_exports_intelligence_decision_workflow_contracts():
    from application import IntelligenceDecisionResult, IntelligenceDecisionWorkflow

    assert IntelligenceDecisionResult
    assert IntelligenceDecisionWorkflow
