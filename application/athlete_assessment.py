from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from application.knowledge_context import AthleteKnowledgeContext
from application.training_assessment import (
    TrainingAssessment,
    TrainingAssessmentStatus,
)


class AthleteAssessmentStatus(Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    STABLE = "stable"
    CAUTION = "caution"


class AthleteAssessmentReason(Enum):
    MISSING_ATHLETE_STATE = "missing_athlete_state"
    NO_TRAINING_DATA = "no_training_data"
    LOW_RECOVERY = "low_recovery"
    HIGH_FATIGUE = "high_fatigue"
    TRAINING_ATTENTION_REQUIRED = "training_attention_required"


@dataclass(frozen=True)
class AthleteAssessment:
    as_of: datetime
    status: AthleteAssessmentStatus
    training_assessment: TrainingAssessment
    reasons: tuple[AthleteAssessmentReason, ...]


class AthleteAssessmentBuilder:
    """Synthesizes existing athlete and training assessments without recalculating them."""

    def build(
        self,
        context: AthleteKnowledgeContext,
        training: TrainingAssessment,
    ) -> AthleteAssessment:

        insufficient_reasons = []

        if context.athlete_state is None:
            insufficient_reasons.append(
                AthleteAssessmentReason.MISSING_ATHLETE_STATE,
            )

        if training.status is TrainingAssessmentStatus.NO_TRAINING_DATA:
            insufficient_reasons.append(
                AthleteAssessmentReason.NO_TRAINING_DATA,
            )

        if insufficient_reasons:
            return self._assessment(
                context,
                training,
                AthleteAssessmentStatus.INSUFFICIENT_DATA,
                tuple(insufficient_reasons),
            )

        athlete = context.athlete_state
        caution_reasons = []

        if athlete.recovery.score < 70:
            caution_reasons.append(
                AthleteAssessmentReason.LOW_RECOVERY,
            )

        if athlete.performance.fatigue >= 80:
            caution_reasons.append(
                AthleteAssessmentReason.HIGH_FATIGUE,
            )

        if training.status is TrainingAssessmentStatus.ATTENTION_REQUIRED:
            caution_reasons.append(
                AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED,
            )

        if caution_reasons:
            return self._assessment(
                context,
                training,
                AthleteAssessmentStatus.CAUTION,
                tuple(caution_reasons),
            )

        return self._assessment(
            context,
            training,
            AthleteAssessmentStatus.STABLE,
            (),
        )

    @staticmethod
    def _assessment(
        context: AthleteKnowledgeContext,
        training: TrainingAssessment,
        status: AthleteAssessmentStatus,
        reasons: tuple[AthleteAssessmentReason, ...],
    ) -> AthleteAssessment:

        return AthleteAssessment(
            as_of=context.as_of,
            status=status,
            training_assessment=training,
            reasons=reasons,
        )
