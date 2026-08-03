from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from athlete.intelligence.models import AthleteInsight, AthleteInsightType
from nutrition import (
    EnergyRequirement,
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionAssessment,
    NutritionDataStatus,
    NutritionRecommendationRule,
)
from recommendation import (
    HydrationRecommendationRule,
    RecommendationBuilder,
    RecommendationContext,
    RecommendationPriority,
    RecommendationRule,
    RecommendationType,
)


AS_OF = datetime(2026, 8, 3, 6, 0)


def _assessment(
    *,
    macros: MacroTargets = MacroTargets(),
    hydration: HydrationTarget = HydrationTarget(),
    confidence: float = 0.625,
    evidence: tuple[str, ...] = ("source:a", "source:b"),
) -> NutritionAssessment:
    return NutritionAssessment(
        energy_requirement=EnergyRequirement(),
        macro_targets=macros,
        fueling_plan=FuelingPlan(),
        hydration_target=hydration,
        data_status=NutritionDataStatus.PARTIAL,
        confidence=confidence,
        evidence=evidence,
        limitations=(),
        valid_for_date=date(2026, 8, 3),
        as_of=AS_OF,
    )


def _context(
    assessment: NutritionAssessment | None = None,
    *,
    insights: tuple[AthleteInsight, ...] = (),
) -> RecommendationContext:
    return RecommendationContext(
        decision=SimpleNamespace(),
        insights=insights,
        observations=(),
        nutrition_assessment=assessment,
    )


def test_context_without_nutrition_assessment_returns_no_recommendations():
    assert NutritionRecommendationRule().evaluate(_context()) == ()


def test_context_keeps_optional_nutrition_assessment_immutable():
    assessment = _assessment()
    context = _context(assessment)

    assert context.nutrition_assessment is assessment
    with pytest.raises(FrozenInstanceError):
        context.nutrition_assessment = None


def test_missing_carbohydrate_target_returns_no_carbohydrate_recommendation():
    recommendations = NutritionRecommendationRule().evaluate(
        _context(
            _assessment(
                hydration=HydrationTarget(daily_ml=2800.0),
            )
        )
    )

    assert all(
        item.type is not RecommendationType.INCREASE_CARBOHYDRATE_INTAKE
        for item in recommendations
    )


def test_carbohydrate_target_returns_global_carbohydrate_recommendation():
    assessment = _assessment(
        macros=MacroTargets(
            carbohydrate_g=360.0,
            carbohydrate_g_per_kg=4.5,
        ),
        confidence=0.75,
    )

    recommendation = NutritionRecommendationRule().evaluate(
        _context(assessment)
    )[0]

    assert (
        recommendation.type
        is RecommendationType.INCREASE_CARBOHYDRATE_INTAKE
    )
    assert recommendation.priority is RecommendationPriority.MEDIUM
    assert recommendation.confidence == assessment.confidence
    assert recommendation.as_of == assessment.as_of
    assert recommendation.source_rules == ("NutritionRecommendationRule",)


def test_missing_hydration_target_returns_no_hydration_recommendation():
    recommendations = NutritionRecommendationRule().evaluate(
        _context(
            _assessment(
                macros=MacroTargets(
                    carbohydrate_g=360.0,
                    carbohydrate_g_per_kg=4.5,
                )
            )
        )
    )

    assert all(
        item.type is not RecommendationType.INCREASE_HYDRATION
        for item in recommendations
    )


def test_hydration_target_returns_global_hydration_recommendation():
    assessment = _assessment(
        hydration=HydrationTarget(
            daily_ml=2800.0,
            daily_ml_per_kg=35.0,
        )
    )

    recommendation = NutritionRecommendationRule().evaluate(
        _context(assessment)
    )[0]

    assert recommendation.type is RecommendationType.INCREASE_HYDRATION
    assert recommendation.priority is RecommendationPriority.MEDIUM
    assert recommendation.confidence == assessment.confidence
    assert recommendation.as_of == AS_OF


def test_rule_can_return_carbohydrate_and_hydration_recommendations():
    assessment = _assessment(
        macros=MacroTargets(
            carbohydrate_g=360.0,
            carbohydrate_g_per_kg=4.5,
        ),
        hydration=HydrationTarget(during_workout_ml_per_hour=500.0),
    )

    recommendations = NutritionRecommendationRule().evaluate(
        _context(assessment)
    )

    assert tuple(item.type for item in recommendations) == (
        RecommendationType.INCREASE_CARBOHYDRATE_INTAKE,
        RecommendationType.INCREASE_HYDRATION,
    )


def test_rule_normalizes_evidence_and_preserves_assessment_timestamp():
    assessment = _assessment(
        macros=MacroTargets(
            carbohydrate_g=360.0,
            carbohydrate_g_per_kg=4.5,
        ),
        evidence=("source:b", "source:a", "source:b"),
    )

    recommendation = NutritionRecommendationRule().evaluate(
        _context(assessment)
    )[0]

    assert recommendation.evidence == ("source:a", "source:b")
    assert recommendation.as_of is assessment.as_of


def test_outputs_are_immutable_and_rule_is_deterministic_without_mutation():
    assessment = _assessment(
        hydration=HydrationTarget(daily_ml=2800.0),
    )
    original = deepcopy(assessment)
    context = _context(assessment)
    rule = NutritionRecommendationRule()

    first = rule.evaluate(context)
    second = rule.evaluate(context)

    assert first == second
    assert assessment == original
    with pytest.raises(FrozenInstanceError):
        first[0].confidence = 0.0


def test_rule_implements_existing_global_recommendation_contract():
    assert isinstance(NutritionRecommendationRule(), RecommendationRule)


def test_global_builder_deduplicates_nutrition_and_recovery_hydration():
    insight = AthleteInsight(
        id="need_more_recovery:event-1",
        type=AthleteInsightType.NEED_MORE_RECOVERY,
        confidence=0.9,
        evidence=("recovery:event-1",),
        as_of=AS_OF,
    )
    assessment = _assessment(
        hydration=HydrationTarget(daily_ml=2800.0),
        confidence=0.75,
        evidence=("nutrition:event-1",),
    )
    context = _context(assessment, insights=(insight,))
    candidates = (
        HydrationRecommendationRule().evaluate(context)
        + NutritionRecommendationRule().evaluate(context)
    )

    result = RecommendationBuilder().build(candidates)

    assert len(result.recommendations) == 1
    recommendation = result.recommendations[0]
    assert recommendation.type is RecommendationType.INCREASE_HYDRATION
    assert recommendation.confidence == 0.9
    assert recommendation.evidence == (
        "nutrition:event-1",
        "recovery:event-1",
    )
    assert recommendation.source_rules == (
        "HydrationRecommendationRule",
        "NutritionRecommendationRule",
    )
