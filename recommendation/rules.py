from datetime import datetime
from typing import Protocol, runtime_checkable

from athlete.intelligence.models import (
    AthleteInsight,
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
)
from decision.prescription.models import DecisionReason
from recommendation.models import (
    Recommendation,
    RecommendationContext,
    RecommendationPriority,
    RecommendationType,
)


@runtime_checkable
class RecommendationRule(Protocol):
    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]: ...


class SleepRecommendationRule:
    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]:
        observations = tuple(
            observation
            for observation in context.observations
            if observation.type is AthleteObservationType.SLEEP_DEBT
        )
        if not observations:
            return ()

        return (
            _recommendation_from_facts(
                recommendation_type=RecommendationType.EXTEND_SLEEP,
                priority=RecommendationPriority.HIGH,
                source_rule=type(self).__name__,
                observations=observations,
            ),
        )


class HydrationRecommendationRule:
    _TRIGGERS = {
        AthleteInsightType.NEED_MORE_RECOVERY,
        AthleteInsightType.FATIGUE_ACCUMULATING,
    }

    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]:
        insights = tuple(
            insight
            for insight in context.insights
            if insight.type in self._TRIGGERS
        )
        if not insights:
            return ()

        return (
            _recommendation_from_facts(
                recommendation_type=RecommendationType.INCREASE_HYDRATION,
                priority=RecommendationPriority.MEDIUM,
                source_rule=type(self).__name__,
                insights=insights,
            ),
        )


class RecoveryRecommendationRule:
    _REDUCE_LOAD_REASON = DecisionReason.ADAPTATION_REDUCE_LOAD.value

    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]:
        insights = tuple(
            insight
            for insight in context.insights
            if insight.type is AthleteInsightType.NEED_MORE_RECOVERY
        )
        reduces_load = any(
            getattr(reason, "value", reason) == self._REDUCE_LOAD_REASON
            for reason in context.decision.decision_reasons
        )
        if not insights and not reduces_load:
            return ()

        evidence = (
            (self._REDUCE_LOAD_REASON,)
            if reduces_load
            else ()
        )
        return (
            _recommendation_from_facts(
                recommendation_type=RecommendationType.APPLY_RECOVERY_PROTOCOL,
                priority=RecommendationPriority.HIGH,
                source_rule=type(self).__name__,
                insights=insights,
                additional_evidence=evidence,
                fallback_confidence=_decision_confidence(context),
                fallback_as_of=_context_as_of(context),
            ),
        )


class MobilityRecommendationRule:
    _TRIGGERS = {
        AthleteInsightType.NEED_MORE_RECOVERY,
        AthleteInsightType.FATIGUE_ACCUMULATING,
    }

    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]:
        insights = tuple(
            insight
            for insight in context.insights
            if insight.type in self._TRIGGERS
        )
        if not insights:
            return ()

        return (
            _recommendation_from_facts(
                recommendation_type=RecommendationType.PERFORM_MOBILITY,
                priority=RecommendationPriority.MEDIUM,
                source_rule=type(self).__name__,
                insights=insights,
            ),
        )


def _recommendation_from_facts(
    recommendation_type: RecommendationType,
    priority: RecommendationPriority,
    source_rule: str,
    insights: tuple[AthleteInsight, ...] = (),
    observations: tuple[AthleteObservation, ...] = (),
    additional_evidence: tuple[str, ...] = (),
    fallback_confidence: float = 0.0,
    fallback_as_of: datetime | None = None,
) -> Recommendation:
    evidence = tuple(
        sorted(
            {
                *additional_evidence,
                *(item for insight in insights for item in insight.evidence),
                *(
                    item
                    for observation in observations
                    for item in observation.evidence
                ),
            }
        )
    )
    confidence = max(
        (
            *(insight.confidence for insight in insights),
            *(observation.confidence for observation in observations),
        ),
        default=fallback_confidence,
    )
    timestamps = (
        *(insight.as_of for insight in insights),
        *(observation.observed_at for observation in observations),
    )
    if not timestamps and fallback_as_of is None:
        raise ValueError(
            "Recommendation requires a dated fact or an explicit fallback_as_of."
        )
    as_of = max(timestamps, default=fallback_as_of)
    identity_evidence = evidence or (source_rule,)

    return Recommendation(
        id=f"{recommendation_type.value}:{':'.join(identity_evidence)}",
        type=recommendation_type,
        priority=priority,
        confidence=confidence,
        evidence=evidence,
        source_rules=(source_rule,),
        as_of=as_of,
    )


def _decision_confidence(context: RecommendationContext) -> float:
    return max(0.0, min(1.0, context.decision.confidence / 100.0))


def _context_as_of(context: RecommendationContext) -> datetime | None:
    return max(
        (
            *(insight.as_of for insight in context.insights),
            *(observation.observed_at for observation in context.observations),
        ),
        default=None,
    )
