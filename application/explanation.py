from dataclasses import dataclass

from application.adaptation import AdaptationDirective, AdaptationStatus
from application.athlete_assessment import (
    AthleteAssessment,
    AthleteAssessmentReason,
)
from planner.models import PlannedWorkout


@dataclass(frozen=True)
class ExplanationReport:
    summary: str
    reasons: tuple[str, ...]


class ExplanationBuilder:
    """Builds deterministic explanations from existing assessment and planning results."""

    REASON_MESSAGES = {
        AthleteAssessmentReason.MISSING_ATHLETE_STATE: (
            "Athlete state is unavailable."
        ),
        AthleteAssessmentReason.NO_TRAINING_DATA: (
            "Training data is unavailable."
        ),
        AthleteAssessmentReason.LOW_RECOVERY: (
            "Recovery status requires reduced load."
        ),
        AthleteAssessmentReason.HIGH_FATIGUE: (
            "Fatigue level requires reduced load."
        ),
        AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED: (
            "Training execution requires reduced load."
        ),
    }

    ADAPTATION_MESSAGES = {
        AdaptationStatus.INSUFFICIENT_DATA: (
            "Long-term adaptation data is insufficient."
        ),
        AdaptationStatus.MAINTAIN: "Long-term adaptation maintains the current plan.",
        AdaptationStatus.REDUCE_LOAD: (
            "Long-term adaptation recommends recovery."
        ),
    }

    def build(
        self,
        assessment: AthleteAssessment,
        adaptation: AdaptationDirective,
        workout: PlannedWorkout,
    ) -> ExplanationReport:

        reasons = tuple(
            self.REASON_MESSAGES[reason]
            for reason in assessment.reasons
        ) + (
            self.ADAPTATION_MESSAGES[adaptation.status],
            f"{workout.name} workout has been selected.",
        )

        return ExplanationReport(
            summary=f"Today's recommendation: {workout.name} ride.",
            reasons=reasons,
        )
