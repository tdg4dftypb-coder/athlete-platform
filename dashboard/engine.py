from __future__ import annotations

from typing import TYPE_CHECKING

from adaptive.models import GoalAssessmentDataStatus
from body_composition.models import BodyCompositionDataStatus
from dashboard.models import (
    AthleteDashboard,
    DashboardSection,
    DashboardSectionStatus,
)
from nutrition.models import NutritionDataStatus

if TYPE_CHECKING:
    from adaptive.models import GoalAssessment
    from body_composition.models import BodyCompositionAssessment
    from decision.models import DecisionResult
    from nutrition.models import NutritionAssessment
    from recommendation.models import Recommendation


_DECISION_TITLE = "Decision"
_BODY_COMPOSITION_TITLE = "Body Composition"
_NUTRITION_TITLE = "Nutrition"
_GOAL_TITLE = "Goal"
_RECOMMENDATIONS_TITLE = "Recommendations"


class DashboardEngine:
    def build(
        self,
        *,
        decision: DecisionResult | None,
        body_composition: BodyCompositionAssessment | None,
        nutrition: NutritionAssessment | None,
        goal: GoalAssessment | None,
        recommendations: tuple[Recommendation, ...],
    ) -> AthleteDashboard:
        return AthleteDashboard(
            decision=self._decision_section(decision),
            body_composition=self._body_composition_section(body_composition),
            nutrition=self._nutrition_section(nutrition),
            goal=self._goal_section(goal),
            recommendations=self._recommendations_section(recommendations),
        )

    @staticmethod
    def _decision_section(
        decision: DecisionResult | None,
    ) -> DashboardSection:
        is_ready = decision is not None
        return DashboardSection(
            title=_DECISION_TITLE,
            status=(
                DashboardSectionStatus.READY
                if is_ready
                else DashboardSectionStatus.UNAVAILABLE
            ),
            confidence=1.0 if is_ready else 0.0,
        )

    @staticmethod
    def _body_composition_section(
        assessment: BodyCompositionAssessment | None,
    ) -> DashboardSection:
        if assessment is None:
            return DashboardSection(
                title=_BODY_COMPOSITION_TITLE,
                status=DashboardSectionStatus.UNAVAILABLE,
                confidence=0.0,
            )

        statuses = {
            BodyCompositionDataStatus.COMPLETE: DashboardSectionStatus.READY,
            BodyCompositionDataStatus.PARTIAL: DashboardSectionStatus.PARTIAL,
            BodyCompositionDataStatus.INSUFFICIENT_DATA: (
                DashboardSectionStatus.UNAVAILABLE
            ),
        }
        return DashboardSection(
            title=_BODY_COMPOSITION_TITLE,
            status=statuses[assessment.data_status],
            confidence=assessment.confidence,
            evidence=assessment.evidence,
            limitations=assessment.limitations,
        )

    @staticmethod
    def _nutrition_section(
        assessment: NutritionAssessment | None,
    ) -> DashboardSection:
        if assessment is None:
            return DashboardSection(
                title=_NUTRITION_TITLE,
                status=DashboardSectionStatus.UNAVAILABLE,
                confidence=0.0,
            )

        statuses = {
            NutritionDataStatus.COMPLETE: DashboardSectionStatus.READY,
            NutritionDataStatus.PARTIAL: DashboardSectionStatus.PARTIAL,
            NutritionDataStatus.INSUFFICIENT_DATA: (
                DashboardSectionStatus.UNAVAILABLE
            ),
        }
        return DashboardSection(
            title=_NUTRITION_TITLE,
            status=statuses[assessment.data_status],
            confidence=assessment.confidence,
            evidence=assessment.evidence,
            limitations=assessment.limitations,
        )

    @staticmethod
    def _goal_section(
        assessment: GoalAssessment | None,
    ) -> DashboardSection:
        if assessment is None:
            return DashboardSection(
                title=_GOAL_TITLE,
                status=DashboardSectionStatus.UNAVAILABLE,
                confidence=0.0,
            )

        statuses = {
            GoalAssessmentDataStatus.COMPLETE: DashboardSectionStatus.READY,
            GoalAssessmentDataStatus.PARTIAL: DashboardSectionStatus.PARTIAL,
            GoalAssessmentDataStatus.INSUFFICIENT_DATA: (
                DashboardSectionStatus.UNAVAILABLE
            ),
        }
        return DashboardSection(
            title=_GOAL_TITLE,
            status=statuses[assessment.data_status],
            confidence=assessment.confidence,
            evidence=assessment.evidence,
            limitations=assessment.limitations,
        )

    @staticmethod
    def _recommendations_section(
        recommendations: tuple[Recommendation, ...],
    ) -> DashboardSection:
        is_ready = bool(recommendations)
        return DashboardSection(
            title=_RECOMMENDATIONS_TITLE,
            status=(
                DashboardSectionStatus.READY
                if is_ready
                else DashboardSectionStatus.UNAVAILABLE
            ),
            confidence=1.0 if is_ready else 0.0,
        )
