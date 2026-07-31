from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from athlete.intelligence.models import (
    AthleteInsight,
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
)
from recommendation import (
    Recommendation,
    RecommendationContext,
    RecommendationPriority,
    RecommendationResult,
    RecommendationType,
)


AS_OF = datetime(2026, 7, 31, 8, 0)


def _recommendation() -> Recommendation:
    return Recommendation(
        id="extend_sleep:sleep-debt-1",
        type=RecommendationType.EXTEND_SLEEP,
        priority=RecommendationPriority.HIGH,
        confidence=0.9,
        evidence=("sleep-debt-1",),
        source_rules=("sleep_debt",),
        as_of=AS_OF,
    )


def test_recommendation_is_immutable_and_keeps_typed_domain_data():
    recommendation = _recommendation()

    assert recommendation.evidence == ("sleep-debt-1",)
    assert recommendation.source_rules == ("sleep_debt",)
    with pytest.raises(FrozenInstanceError):
        recommendation.confidence = 0.5


def test_recommendation_type_and_priority_sets_match_the_v1_contract():
    assert set(RecommendationType) == {
        RecommendationType.EXTEND_SLEEP,
        RecommendationType.INCREASE_HYDRATION,
        RecommendationType.INCREASE_CARBOHYDRATE_INTAKE,
        RecommendationType.PERFORM_MOBILITY,
        RecommendationType.LIMIT_ADDITIONAL_ACTIVITY,
        RecommendationType.APPLY_RECOVERY_PROTOCOL,
    }
    assert set(RecommendationPriority) == {
        RecommendationPriority.HIGH,
        RecommendationPriority.MEDIUM,
        RecommendationPriority.LOW,
    }


def test_recommendation_result_is_immutable_and_accepts_an_empty_result():
    result = RecommendationResult(recommendations=(), as_of=AS_OF)

    assert result.recommendations == ()
    with pytest.raises(FrozenInstanceError):
        result.recommendations = (_recommendation(),)


def test_recommendation_context_is_immutable_and_keeps_prepared_inputs():
    observation = AthleteObservation(
        id="sleep_debt:sleep-debt-1",
        type=AthleteObservationType.SLEEP_DEBT,
        value=60.0,
        confidence=1.0,
        observed_at=AS_OF,
        evidence=("sleep-debt-1",),
    )
    insight = AthleteInsight(
        id="need_more_recovery:sleep-debt-1",
        type=AthleteInsightType.NEED_MORE_RECOVERY,
        confidence=1.0,
        evidence=("sleep-debt-1",),
        as_of=AS_OF,
    )
    decision = object()

    context = RecommendationContext(
        decision=decision,
        insights=(insight,),
        observations=(observation,),
    )

    assert context.decision is decision
    assert context.insights == (insight,)
    assert context.observations == (observation,)
    with pytest.raises(FrozenInstanceError):
        context.insights = ()
