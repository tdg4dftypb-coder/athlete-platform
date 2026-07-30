from dataclasses import dataclass

from application.adaptation import AdaptationDirective, AdaptationStatus
from application.athlete_assessment import AthleteAssessment
from application.explanation import ExplanationBuilder, ExplanationReport
from athlete.models import AthleteState
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
