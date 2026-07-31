from datetime import datetime
from types import SimpleNamespace

from athlete.intelligence.models import (
    AthleteInsight,
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
)
from recommendation import (
    HydrationRecommendationRule,
    MobilityRecommendationRule,
    RecommendationContext,
    RecommendationPriority,
    RecommendationRule,
    RecommendationType,
    RecoveryRecommendationRule,
    SleepRecommendationRule,
)


AS_OF = datetime(2026, 7, 31, 8)


def _decision(*reasons: str, confidence: float = 80.0) -> SimpleNamespace:
    decision_reasons = tuple(
        SimpleNamespace(value=reason)
        for reason in reasons
    )
    return SimpleNamespace(
        decision_reasons=decision_reasons,
        confidence=confidence,
    )


def _insight(insight_type: AthleteInsightType) -> AthleteInsight:
    return AthleteInsight(
        id=f"{insight_type.value}:event-1",
        type=insight_type,
        confidence=0.9,
        evidence=("event-1",),
        as_of=AS_OF,
    )


def _observation(
    observation_type: AthleteObservationType,
) -> AthleteObservation:
    return AthleteObservation(
        id=f"{observation_type.value}:event-1",
        type=observation_type,
        value=60.0,
        confidence=0.8,
        observed_at=AS_OF,
        evidence=("event-1",),
    )


def _context(
    *,
    insights: tuple[AthleteInsight, ...] = (),
    observations: tuple[AthleteObservation, ...] = (),
    decision: SimpleNamespace | None = None,
) -> RecommendationContext:
    return RecommendationContext(
        decision=decision or _decision(),
        insights=insights,
        observations=observations,
    )


def test_sleep_rule_recommends_more_sleep_for_sleep_debt():
    context = _context(
        observations=(_observation(AthleteObservationType.SLEEP_DEBT),),
    )

    recommendations = SleepRecommendationRule().evaluate(context)

    assert len(recommendations) == 1
    assert recommendations[0].type is RecommendationType.EXTEND_SLEEP
    assert recommendations[0].priority is RecommendationPriority.HIGH
    assert recommendations[0].evidence == ("event-1",)
    assert recommendations[0].as_of == AS_OF
    assert SleepRecommendationRule().evaluate(context) == recommendations


def test_sleep_rule_returns_empty_without_sleep_debt():
    context = _context(
        observations=(_observation(AthleteObservationType.RECOVERY_GOOD),),
    )

    assert SleepRecommendationRule().evaluate(context) == ()


def test_hydration_rule_recommends_hydration_for_increased_recovery_need():
    context = _context(
        insights=(_insight(AthleteInsightType.NEED_MORE_RECOVERY),),
    )

    recommendations = HydrationRecommendationRule().evaluate(context)

    assert len(recommendations) == 1
    assert recommendations[0].type is RecommendationType.INCREASE_HYDRATION
    assert recommendations[0].priority is RecommendationPriority.MEDIUM
    assert recommendations[0].confidence == 0.9


def test_hydration_rule_returns_empty_without_increased_recovery_need():
    context = _context(
        insights=(_insight(AthleteInsightType.HIGH_TRAINING_COMPLIANCE),),
    )

    assert HydrationRecommendationRule().evaluate(context) == ()


def test_recovery_rule_recommends_protocol_for_recovery_insight():
    context = _context(
        insights=(_insight(AthleteInsightType.NEED_MORE_RECOVERY),),
    )

    recommendations = RecoveryRecommendationRule().evaluate(context)

    assert len(recommendations) == 1
    assert recommendations[0].type is RecommendationType.APPLY_RECOVERY_PROTOCOL
    assert recommendations[0].priority is RecommendationPriority.HIGH
    assert recommendations[0].source_rules == ("RecoveryRecommendationRule",)


def test_recovery_rule_recommends_protocol_for_load_reduction_decision():
    context = _context(
        decision=_decision("adaptation_reduce_load", confidence=75.0),
        observations=(_observation(AthleteObservationType.TRAINING_LOAD_HIGH),),
    )

    recommendation = RecoveryRecommendationRule().evaluate(context)[0]

    assert recommendation.type is RecommendationType.APPLY_RECOVERY_PROTOCOL
    assert recommendation.confidence == 0.75
    assert recommendation.evidence == ("adaptation_reduce_load",)
    assert recommendation.as_of == AS_OF


def test_recovery_rule_returns_empty_without_recovery_signal():
    assert RecoveryRecommendationRule().evaluate(_context()) == ()


def test_mobility_rule_recommends_mobility_for_limited_recovery():
    context = _context(
        insights=(_insight(AthleteInsightType.FATIGUE_ACCUMULATING),),
    )

    recommendations = MobilityRecommendationRule().evaluate(context)

    assert len(recommendations) == 1
    assert recommendations[0].type is RecommendationType.PERFORM_MOBILITY
    assert recommendations[0].priority is RecommendationPriority.MEDIUM


def test_mobility_rule_returns_empty_without_recovery_limitation():
    context = _context(
        insights=(_insight(AthleteInsightType.HIGH_TRAINING_COMPLIANCE),),
    )

    assert MobilityRecommendationRule().evaluate(context) == ()


def test_all_rules_implement_the_recommendation_rule_contract():
    assert all(
        isinstance(rule, RecommendationRule)
        for rule in (
            SleepRecommendationRule(),
            HydrationRecommendationRule(),
            RecoveryRecommendationRule(),
            MobilityRecommendationRule(),
        )
    )
