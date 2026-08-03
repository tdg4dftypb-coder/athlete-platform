from adaptive.models import GoalAssessmentDataStatus
from recommendation import (
    Recommendation,
    RecommendationContext,
    RecommendationPriority,
    RecommendationRule,
    RecommendationType,
)


class AdaptiveGoalRecommendationRule(RecommendationRule):
    """Map only a fully complete goal assessment to a neutral review action."""

    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]:
        assessment = context.goal_assessment
        if (
            assessment is None
            or assessment.data_status is not GoalAssessmentDataStatus.COMPLETE
            or assessment.confidence != 1.0
            or assessment.limitations
            or assessment.goal is None
        ):
            return ()

        source_rule = type(self).__name__
        recommendation_type = RecommendationType.REVIEW_BODY_COMPOSITION_TREND
        return (
            Recommendation(
                id=f"{recommendation_type.value}:{source_rule}",
                type=recommendation_type,
                priority=RecommendationPriority.MEDIUM,
                confidence=assessment.confidence,
                evidence=assessment.evidence,
                source_rules=(source_rule,),
                as_of=assessment.as_of,
            ),
        )
