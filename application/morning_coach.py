from dataclasses import dataclass

from application.adaptation import AdaptationDirective, AdaptationStatus
from application.athlete_assessment import AthleteAssessment
from application.explanation import ExplanationBuilder, ExplanationReport
from application.intelligence_decision_workflow import IntelligenceDecisionResult
from athlete.models import AthleteState
from athlete.review.models import WeeklyTrainingReview
from planner.models import PlannedWorkout


@dataclass(frozen=True)
class MorningCoachReport:
    athlete_state: AthleteState
    athlete_assessment: AthleteAssessment
    adaptation: AdaptationDirective
    workout: PlannedWorkout
    explanation: ExplanationReport
    message: str


class MorningCoachBuilder:
    """Creates a deterministic daily brief from already prepared application results."""

    def build(
        self,
        athlete_state: AthleteState,
        athlete_assessment: AthleteAssessment,
        adaptation: AdaptationDirective,
        workout: PlannedWorkout,
    ) -> MorningCoachReport:

        return MorningCoachReport(
            athlete_state=athlete_state,
            athlete_assessment=athlete_assessment,
            adaptation=adaptation,
            workout=workout,
            explanation=ExplanationBuilder().build(
                athlete_assessment,
                adaptation,
                workout,
            ),
            message=self._message_for(adaptation, workout),
        )

    @staticmethod
    def _message_for(
        adaptation: AdaptationDirective,
        workout: PlannedWorkout,
    ) -> str:

        return _morning_coach_message(adaptation, workout)


def _morning_coach_message(
    adaptation: AdaptationDirective,
    workout: PlannedWorkout,
) -> str:

    reasons = {
        AdaptationStatus.INSUFFICIENT_DATA: (
            "Insufficient data for long-term adaptation."
        ),
        AdaptationStatus.MAINTAIN: "Current plan is maintained.",
        AdaptationStatus.REDUCE_LOAD: (
            "Long-term adaptation requires reduced load."
        ),
    }

    return (
        f"Dzisiaj zalecany trening: {workout.name}. "
        f"Powód: {reasons[adaptation.status]}"
    )


class MorningCoachPresenter:
    def present(
        self,
        intelligence: IntelligenceDecisionResult,
        planned_workout: PlannedWorkout,
        athlete_state: AthleteState,
        athlete_assessment: AthleteAssessment,
        weekly_review: WeeklyTrainingReview,
        adaptation: AdaptationDirective,
    ) -> MorningCoachReport:
        return MorningCoachReport(
            athlete_state=athlete_state,
            athlete_assessment=athlete_assessment,
            adaptation=adaptation,
            workout=planned_workout,
            explanation=ExplanationReport(
                summary=intelligence.explainability.summary,
                reasons=(
                    intelligence.explainability.contributing_factors
                    + intelligence.explainability.recommendations
                ),
            ),
            message=_morning_coach_message(
                adaptation,
                planned_workout,
            ),
        )
