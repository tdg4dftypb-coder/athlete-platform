from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from adaptive import AdaptiveGoalRecommendationRule
from application import (
    AdaptationDirective,
    AdaptationStatus,
    ExplainabilityResult,
    IntelligenceDecisionWorkflow,
    build_default_recommendation_engine,
)
from application.body_composition_input import BodyCompositionInputBuilder
from athlete.intelligence.models import (
    AthleteInsightType,
    AthleteObservationType,
    HealthObservationInput,
)
from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionEngine,
    BodyCompositionInput,
    BodyCompositionProfile,
)
from core.models import HealthDaily
from decision.engine import DecisionEngine
from decision.prescription.models import DecisionReason, TrainingObjective
from nutrition import (
    EnergyRequirement,
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionAssessment,
    NutritionDataStatus,
    NutritionInput,
    NutritionRecommendationRule,
)
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


class SpyNutritionInputBuilder:
    def __init__(self, result: NutritionInput, calls: list[str]) -> None:
        self.result = result
        self.calls = calls
        self.arguments = []

    def build(self, decision, **kwargs):
        self.calls.append("nutrition_input")
        self.arguments.append((decision, kwargs))
        return self.result


class SpyNutritionEngine:
    def __init__(self, result: NutritionAssessment, calls: list[str]) -> None:
        self.result = result
        self.calls = calls
        self.inputs = []

    def analyze(self, nutrition_input):
        self.calls.append("nutrition")
        self.inputs.append(nutrition_input)
        return self.result


class SpyBodyCompositionInputBuilder:
    def __init__(self, result: BodyCompositionInput, calls: list[str]) -> None:
        self.result = result
        self.calls = calls
        self.arguments = []

    def build(self, **kwargs):
        self.calls.append("body_composition_input")
        self.arguments.append(kwargs)
        return self.result


class SpyBodyCompositionEngine:
    def __init__(
        self,
        result: BodyCompositionAssessment,
        calls: list[str],
    ) -> None:
        self.result = result
        self.calls = calls
        self.inputs = []

    def analyze(self, body_composition_input):
        self.calls.append("body_composition")
        self.inputs.append(body_composition_input)
        return self.result


class OrderedDecisionEngine:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.engine = DecisionEngine()
        self.arguments = []

    def decide(self, *args, **kwargs):
        self.calls.append("decision")
        self.arguments.append((args, kwargs))
        return self.engine.decide(*args, **kwargs)


class OrderedExplainabilityBuilder(SpyExplainabilityBuilder):
    def __init__(self, calls: list[str]) -> None:
        super().__init__()
        self.ordered_calls = calls

    def build(self, decision_reasons, recommendations):
        self.ordered_calls.append("explainability")
        return super().build(decision_reasons, recommendations)


class OrderedRecommendationEngine(SpyRecommendationEngine):
    def __init__(self, result: RecommendationResult, calls: list[str]) -> None:
        super().__init__(result)
        self.calls = calls

    def evaluate(self, context):
        self.calls.append("recommendation")
        return super().evaluate(context)


def _nutrition_assessment(as_of: datetime) -> NutritionAssessment:
    return NutritionAssessment(
        energy_requirement=EnergyRequirement(),
        macro_targets=MacroTargets(),
        fueling_plan=FuelingPlan(),
        hydration_target=HydrationTarget(),
        data_status=NutritionDataStatus.INSUFFICIENT_DATA,
        confidence=0.0,
        evidence=(),
        limitations=(),
        valid_for_date=as_of.date(),
        as_of=as_of,
    )


def _body_composition_assessment(
    as_of: datetime,
) -> BodyCompositionAssessment:
    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(),
        body_mass_trend=None,
        data_status=BodyCompositionDataStatus.INSUFFICIENT_DATA,
        confidence=0.0,
        evidence=(),
        limitations=(
            "missing_body_mass",
            "missing_body_fat_percentage",
            "missing_muscle_mass",
            "missing_body_water_percentage",
            "missing_visceral_fat",
            "missing_basal_metabolic_rate",
            "missing_waist_circumference",
            "insufficient_body_mass_history",
        ),
        valid_for_date=as_of.date(),
        as_of=as_of,
    )


def test_workflow_runs_body_composition_once_in_canonical_order():
    as_of = datetime(2026, 8, 3, 6)
    health = HealthObservationInput(
        observed_at=as_of,
        hrv_delta_percent=None,
        sleep_duration_minutes=None,
        sleep_baseline_minutes=None,
        recovery_score=80.0,
        evidence=("health-day",),
    )
    health_history = (HealthDaily(as_of.date(), weight=80.0),)
    body_input = BodyCompositionInput((), as_of.date(), as_of)
    body_assessment = _body_composition_assessment(as_of)
    nutrition_input = NutritionInput(valid_for_date=as_of.date(), as_of=as_of)
    nutrition_assessment = _nutrition_assessment(as_of)
    calls: list[str] = []
    body_input_builder = SpyBodyCompositionInputBuilder(body_input, calls)
    body_engine = SpyBodyCompositionEngine(body_assessment, calls)
    nutrition_input_builder = SpyNutritionInputBuilder(nutrition_input, calls)
    nutrition_engine = SpyNutritionEngine(nutrition_assessment, calls)
    recommendation_engine = OrderedRecommendationEngine(
        RecommendationResult((), None),
        calls,
    )
    explainability_builder = OrderedExplainabilityBuilder(calls)
    original_history = deepcopy(health_history)

    result = IntelligenceDecisionWorkflow(
        decision_engine=OrderedDecisionEngine(calls),
        body_composition_input_builder=body_input_builder,
        body_composition_engine=body_engine,
        nutrition_input_builder=nutrition_input_builder,
        nutrition_engine=nutrition_engine,
        recommendation_engine=recommendation_engine,
        explainability_builder=explainability_builder,
    ).run(
        build_athlete(),
        health=health,
        nutrition_health_history=health_history,
        body_composition_health_history=health_history,
    )

    assert calls == [
        "decision",
        "body_composition_input",
        "body_composition",
        "nutrition_input",
        "nutrition",
        "recommendation",
        "explainability",
    ]
    assert body_input_builder.arguments == [
        {"health_history": health_history, "as_of": as_of}
    ]
    assert body_engine.inputs == [body_input]
    assert nutrition_engine.inputs == [nutrition_input]
    assert result.body_composition is body_assessment
    assert result.nutrition is nutrition_assessment
    assert len(recommendation_engine.contexts) == 1
    recommendation_context = recommendation_engine.contexts[0]
    assert not hasattr(recommendation_context, "body_composition")
    assert not hasattr(recommendation_context, "body_composition_assessment")
    assert explainability_builder.calls == [
        (result.decision.decision_reasons, result.recommendations)
    ]
    assert health_history == original_history
    with pytest.raises(FrozenInstanceError):
        result.body_composition = None


def test_workflow_returns_an_insufficient_assessment_for_empty_body_history():
    as_of = datetime(2026, 8, 3, 6)
    health = HealthObservationInput(
        observed_at=as_of,
        hrv_delta_percent=None,
        sleep_duration_minutes=None,
        sleep_baseline_minutes=None,
        recovery_score=None,
        evidence=(),
    )

    result = IntelligenceDecisionWorkflow().run(
        build_athlete(),
        health=health,
        body_composition_health_history=(),
    )

    assert result.body_composition is not None
    assert (
        result.body_composition.data_status
        is BodyCompositionDataStatus.INSUFFICIENT_DATA
    )


def test_workflow_reuses_the_existing_health_history_for_compatible_call_sites():
    as_of = datetime(2026, 8, 3, 6)
    history = (HealthDaily(as_of.date(), weight=80.0),)

    result = IntelligenceDecisionWorkflow().run(
        build_athlete(),
        nutrition_health_history=history,
    )

    assert result.body_composition is not None
    assert result.body_composition.profile.body_mass is not None
    assert result.body_composition.profile.body_mass.value == 80.0


def test_workflow_body_composition_is_deterministic_and_does_not_mutate_history():
    as_of = datetime(2026, 8, 3, 6)
    health = HealthObservationInput(
        observed_at=as_of,
        hrv_delta_percent=None,
        sleep_duration_minutes=None,
        sleep_baseline_minutes=None,
        recovery_score=None,
        evidence=(),
    )
    history = (
        HealthDaily(date(2026, 7, 6), weight=81.0),
        HealthDaily(date(2026, 8, 3), weight=80.0),
    )
    original = deepcopy(history)
    workflow = IntelligenceDecisionWorkflow(
        body_composition_input_builder=BodyCompositionInputBuilder(),
        body_composition_engine=BodyCompositionEngine(),
    )

    first = workflow.run(
        build_athlete(),
        health=health,
        body_composition_health_history=history,
    )
    second = workflow.run(
        build_athlete(),
        health=health,
        body_composition_health_history=history,
    )

    assert first == second
    assert first.body_composition == second.body_composition
    assert history == original


def test_workflow_runs_nutrition_once_before_the_single_recommendation_pass():
    as_of = datetime(2026, 8, 3, 6)
    health = HealthObservationInput(
        observed_at=as_of,
        hrv_delta_percent=None,
        sleep_duration_minutes=None,
        sleep_baseline_minutes=None,
        recovery_score=80.0,
        evidence=("health-day",),
    )
    nutrition_input = NutritionInput(
        valid_for_date=date(2026, 8, 3),
        as_of=as_of,
    )
    assessment = _nutrition_assessment(as_of)
    calls: list[str] = []
    input_builder = SpyNutritionInputBuilder(nutrition_input, calls)
    nutrition_engine = SpyNutritionEngine(assessment, calls)
    recommendation_engine = OrderedRecommendationEngine(
        RecommendationResult((), None),
        calls,
    )
    original_health = deepcopy(health)

    result = IntelligenceDecisionWorkflow(
        nutrition_input_builder=input_builder,
        nutrition_engine=nutrition_engine,
        recommendation_engine=recommendation_engine,
    ).run(build_athlete(), health=health)

    assert calls == ["nutrition_input", "nutrition", "recommendation"]
    assert nutrition_engine.inputs == [nutrition_input]
    assert len(recommendation_engine.contexts) == 1
    assert recommendation_engine.contexts[0].nutrition_assessment is assessment
    assert result.nutrition is assessment
    assert input_builder.arguments[0][0] is result.decision
    assert health == original_health


def test_workflow_nutrition_integration_is_deterministic_between_runs():
    as_of = datetime(2026, 8, 3, 6)
    health = HealthObservationInput(
        observed_at=as_of,
        hrv_delta_percent=None,
        sleep_duration_minutes=None,
        sleep_baseline_minutes=None,
        recovery_score=80.0,
        evidence=(),
    )
    workflow = IntelligenceDecisionWorkflow()

    first = workflow.run(build_athlete(), health=health)
    second = workflow.run(build_athlete(), health=health)

    assert first == second
    assert first.nutrition == second.nutrition


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


def test_workflow_passes_built_insights_to_decision_engine_exactly_once():
    calls: list[str] = []
    decision_engine = OrderedDecisionEngine(calls)
    health = HealthObservationInput(
        observed_at=datetime(2026, 7, 1, 8),
        hrv_delta_percent=-5.0,
        sleep_duration_minutes=360.0,
        sleep_baseline_minutes=420.0,
        recovery_score=None,
        evidence=("health-day-1",),
    )

    result = IntelligenceDecisionWorkflow(
        decision_engine=decision_engine,
    ).run(build_athlete(), health=health)

    assert calls.count("decision") == 1
    assert len(decision_engine.arguments) == 1
    args, kwargs = decision_engine.arguments[0]
    assert kwargs == {}
    assert args[2] is result.insights


def test_application_public_api_does_not_expose_decision_input():
    import application

    assert "DecisionInput" not in application.__all__
    assert not hasattr(application, "DecisionInput")


def test_workflow_supports_an_empty_recommendation_result():
    expected = RecommendationResult((), None)

    result = IntelligenceDecisionWorkflow(
        recommendation_engine=SpyRecommendationEngine(expected),
    ).run(build_athlete())

    assert result.recommendations is expected
    assert result.explainability.recommendations == ()


def test_default_composition_contains_the_six_recommendation_rules():
    engine = build_default_recommendation_engine()

    assert tuple(type(rule) for rule in engine._rules) == (
        SleepRecommendationRule,
        HydrationRecommendationRule,
        RecoveryRecommendationRule,
        MobilityRecommendationRule,
        NutritionRecommendationRule,
        AdaptiveGoalRecommendationRule,
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
    ) == (
        RecommendationType.APPLY_RECOVERY_PROTOCOL,
        RecommendationType.INCREASE_HYDRATION,
    )


def test_application_exports_intelligence_decision_workflow_contracts():
    from application import IntelligenceDecisionResult, IntelligenceDecisionWorkflow

    assert IntelligenceDecisionResult
    assert IntelligenceDecisionWorkflow
