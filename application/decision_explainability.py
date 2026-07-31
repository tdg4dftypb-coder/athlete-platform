from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from decision.prescription.models import DecisionReason
from recommendation.models import RecommendationResult, RecommendationType


class ExplainabilityMappingError(ValueError):
    pass


@dataclass(frozen=True)
class ExplainabilityResult:
    summary: str
    contributing_factors: tuple[str, ...]
    recommendations: tuple[str, ...]


class DecisionExplainabilityBuilder:
    """Renders neutral application explanations from structured decision reasons."""

    _FACTOR_MESSAGES = {
        DecisionReason.ADAPTATION_REDUCE_LOAD: (
            "Training load reduced due to adaptation."
        ),
        DecisionReason.INSIGHT_NEED_MORE_RECOVERY: (
            "Recovery requirements detected."
        ),
        DecisionReason.INSIGHT_FATIGUE_ACCUMULATING: (
            "Accumulated fatigue detected."
        ),
        DecisionReason.INSIGHT_HIGH_TRAINING_COMPLIANCE: (
            "High training compliance detected."
        ),
    }
    _RECOMMENDATION_MESSAGES = {
        RecommendationType.EXTEND_SLEEP: "Extend sleep duration.",
        RecommendationType.INCREASE_HYDRATION: "Increase hydration.",
        RecommendationType.INCREASE_CARBOHYDRATE_INTAKE: (
            "Increase carbohydrate intake."
        ),
        RecommendationType.PERFORM_MOBILITY: "Perform mobility work.",
        RecommendationType.LIMIT_ADDITIONAL_ACTIVITY: (
            "Limit additional activity."
        ),
        RecommendationType.APPLY_RECOVERY_PROTOCOL: (
            "Apply recovery protocol."
        ),
    }

    def __init__(self) -> None:
        self._validate_mapping(
            "decision reason",
            DecisionReason,
            self._FACTOR_MESSAGES,
        )
        self._validate_mapping(
            "recommendation type",
            RecommendationType,
            self._RECOMMENDATION_MESSAGES,
        )

    def build(
        self,
        decision_reasons: tuple[DecisionReason, ...],
        recommendation_result: RecommendationResult | None = None,
    ) -> ExplainabilityResult:
        factors = tuple(
            self._mapped_message("decision reason", reason, self._FACTOR_MESSAGES)
            for reason in decision_reasons
        )
        recommendations = (
            recommendation_result.recommendations
            if recommendation_result is not None
            else ()
        )

        return ExplainabilityResult(
            summary=(
                "Decision factors identified."
                if factors
                else "No additional decision factors detected."
            ),
            contributing_factors=factors,
            recommendations=tuple(
                self._mapped_message(
                    "recommendation type",
                    recommendation.type,
                    self._RECOMMENDATION_MESSAGES,
                )
                for recommendation in recommendations
            ),
        )

    @staticmethod
    def _validate_mapping(
        name: str,
        enum_type: type[Enum],
        mapping: Mapping[object, str],
    ) -> None:
        missing = set(enum_type) - set(mapping)
        if missing:
            values = ", ".join(sorted(item.value for item in missing))
            raise ExplainabilityMappingError(
                f"Missing {name} explainability mappings: {values}"
            )

    @staticmethod
    def _mapped_message(
        name: str,
        key: object,
        mapping: Mapping[object, str],
    ) -> str:
        try:
            return mapping[key]
        except KeyError as error:
            value = getattr(key, "value", repr(key))
            raise ExplainabilityMappingError(
                f"Missing {name} explainability mapping: {value}"
            ) from error
