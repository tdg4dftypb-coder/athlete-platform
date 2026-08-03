from nutrition.models import NutritionAssessment
from recommendation import (
    Recommendation,
    RecommendationContext,
    RecommendationPriority,
    RecommendationRule,
    RecommendationType,
)


class NutritionRecommendationRule(RecommendationRule):
    """Map available nutrition targets to existing recommendation actions."""

    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]:
        assessment = context.nutrition_assessment
        if assessment is None:
            return ()

        recommendations: list[Recommendation] = []
        macros = assessment.macro_targets
        if (
            macros.carbohydrate_g is not None
            and macros.carbohydrate_g_per_kg is not None
        ):
            recommendations.append(
                self._recommendation(
                    assessment,
                    RecommendationType.INCREASE_CARBOHYDRATE_INTAKE,
                    RecommendationPriority.MEDIUM,
                )
            )

        hydration = assessment.hydration_target
        if any(
            value is not None
            for value in (
                hydration.daily_ml,
                hydration.daily_ml_per_kg,
                hydration.pre_workout_ml,
                hydration.during_workout_ml_per_hour,
                hydration.post_workout_ml,
            )
        ):
            recommendations.append(
                self._recommendation(
                    assessment,
                    RecommendationType.INCREASE_HYDRATION,
                    RecommendationPriority.MEDIUM,
                )
            )

        return tuple(recommendations)

    def _recommendation(
        self,
        assessment: NutritionAssessment,
        recommendation_type: RecommendationType,
        priority: RecommendationPriority,
    ) -> Recommendation:
        source_rule = type(self).__name__
        return Recommendation(
            id=f"{recommendation_type.value}:{source_rule}",
            type=recommendation_type,
            priority=priority,
            confidence=assessment.confidence,
            evidence=tuple(sorted(set(assessment.evidence))),
            source_rules=(source_rule,),
            as_of=assessment.as_of,
        )
