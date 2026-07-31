from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from application import (
    DecisionExplainabilityBuilder,
    ExplainabilityMappingError,
    ExplainabilityResult,
)
from decision.prescription.models import DecisionReason
from recommendation import (
    Recommendation,
    RecommendationPriority,
    RecommendationResult,
    RecommendationType,
)


AS_OF = datetime(2026, 7, 31, 8)


def _recommendation(
    recommendation_type: RecommendationType,
    recommendation_id: str,
) -> Recommendation:
    return Recommendation(
        id=recommendation_id,
        type=recommendation_type,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.8,
        evidence=("event-1",),
        source_rules=("Rule",),
        as_of=AS_OF,
    )


@pytest.mark.parametrize(
    ("reason", "expected_factor"),
    [
        (
            DecisionReason.INSIGHT_NEED_MORE_RECOVERY,
            "Recovery requirements detected.",
        ),
        (
            DecisionReason.INSIGHT_FATIGUE_ACCUMULATING,
            "Accumulated fatigue detected.",
        ),
        (
            DecisionReason.ADAPTATION_REDUCE_LOAD,
            "Training load reduced due to adaptation.",
        ),
        (
            DecisionReason.INSIGHT_HIGH_TRAINING_COMPLIANCE,
            "High training compliance detected.",
        ),
    ],
)
def test_builder_maps_each_structural_decision_reason(reason, expected_factor):
    result = DecisionExplainabilityBuilder().build((reason,))

    assert result.summary == "Decision factors identified."
    assert result.contributing_factors == (expected_factor,)
    assert result.recommendations == ()


def test_builder_preserves_decision_reason_order_for_multiple_factors():
    result = DecisionExplainabilityBuilder().build(
        (
            DecisionReason.INSIGHT_NEED_MORE_RECOVERY,
            DecisionReason.INSIGHT_FATIGUE_ACCUMULATING,
            DecisionReason.INSIGHT_HIGH_TRAINING_COMPLIANCE,
        )
    )

    assert result.contributing_factors == (
        "Recovery requirements detected.",
        "Accumulated fatigue detected.",
        "High training compliance detected.",
    )


def test_builder_returns_a_neutral_result_for_empty_decision_reasons():
    result = DecisionExplainabilityBuilder().build(())

    assert result.summary == "No additional decision factors detected."
    assert result.contributing_factors == ()
    assert result.recommendations == ()


@pytest.mark.parametrize(
    ("recommendation_type", "expected_message"),
    [
        (RecommendationType.EXTEND_SLEEP, "Extend sleep duration."),
        (RecommendationType.INCREASE_HYDRATION, "Increase hydration."),
        (
            RecommendationType.INCREASE_CARBOHYDRATE_INTAKE,
            "Increase carbohydrate intake.",
        ),
        (RecommendationType.PERFORM_MOBILITY, "Perform mobility work."),
        (
            RecommendationType.LIMIT_ADDITIONAL_ACTIVITY,
            "Limit additional activity.",
        ),
        (
            RecommendationType.APPLY_RECOVERY_PROTOCOL,
            "Apply recovery protocol.",
        ),
    ],
)
def test_builder_maps_every_recommendation_type(
    recommendation_type,
    expected_message,
):
    recommendation = _recommendation(recommendation_type, "recommendation-1")
    recommendation_result = RecommendationResult((recommendation,), AS_OF)

    result = DecisionExplainabilityBuilder().build((), recommendation_result)

    assert result.recommendations == (expected_message,)


def test_builder_preserves_recommendation_order_and_duplicates():
    recommendations = (
        _recommendation(RecommendationType.PERFORM_MOBILITY, "mobility-1"),
        _recommendation(RecommendationType.EXTEND_SLEEP, "sleep-1"),
        _recommendation(RecommendationType.PERFORM_MOBILITY, "mobility-2"),
    )

    result = DecisionExplainabilityBuilder().build(
        (DecisionReason.INSIGHT_NEED_MORE_RECOVERY,),
        RecommendationResult(recommendations, AS_OF),
    )

    assert result.contributing_factors == ("Recovery requirements detected.",)
    assert result.recommendations == (
        "Perform mobility work.",
        "Extend sleep duration.",
        "Perform mobility work.",
    )


def test_builder_rejects_an_incomplete_recommendation_mapping():
    class IncompleteBuilder(DecisionExplainabilityBuilder):
        _RECOMMENDATION_MESSAGES = {
            key: value
            for key, value in (
                DecisionExplainabilityBuilder._RECOMMENDATION_MESSAGES.items()
            )
            if key is not RecommendationType.EXTEND_SLEEP
        }

    with pytest.raises(ExplainabilityMappingError, match="extend_sleep"):
        IncompleteBuilder()


def test_builder_rejects_an_incomplete_decision_reason_mapping():
    class IncompleteBuilder(DecisionExplainabilityBuilder):
        _FACTOR_MESSAGES = {
            key: value
            for key, value in DecisionExplainabilityBuilder._FACTOR_MESSAGES.items()
            if key is not DecisionReason.ADAPTATION_REDUCE_LOAD
        }

    with pytest.raises(ExplainabilityMappingError, match="adaptation_reduce_load"):
        IncompleteBuilder()


def test_builder_is_deterministic_and_result_is_immutable():
    builder = DecisionExplainabilityBuilder()
    reasons = (DecisionReason.INSIGHT_NEED_MORE_RECOVERY,)

    result = builder.build(reasons)

    assert builder.build(reasons) == result
    with pytest.raises(FrozenInstanceError):
        result.summary = "Changed"


def test_application_exports_explainability_contracts():
    assert DecisionExplainabilityBuilder
    assert ExplainabilityResult
