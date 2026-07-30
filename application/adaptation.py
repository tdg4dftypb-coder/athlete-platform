from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from application.athlete_assessment import (
    AthleteAssessment,
    AthleteAssessmentReason,
    AthleteAssessmentStatus,
)


class AdaptationStatus(Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    MAINTAIN = "maintain"
    REDUCE_LOAD = "reduce_load"


@dataclass(frozen=True)
class AdaptationDirective:
    as_of: datetime
    status: AdaptationStatus
    source_reasons: tuple[AthleteAssessmentReason, ...]


class AdaptationPolicy:
    """Maps a completed athlete assessment to a deterministic adaptation directive."""

    def evaluate(
        self,
        assessment: AthleteAssessment,
    ) -> AdaptationDirective:

        if assessment.status is AthleteAssessmentStatus.INSUFFICIENT_DATA:
            return self._directive(
                assessment,
                AdaptationStatus.INSUFFICIENT_DATA,
                assessment.reasons,
            )

        if assessment.status is AthleteAssessmentStatus.CAUTION:
            return self._directive(
                assessment,
                AdaptationStatus.REDUCE_LOAD,
                assessment.reasons,
            )

        return self._directive(
            assessment,
            AdaptationStatus.MAINTAIN,
            (),
        )

    @staticmethod
    def _directive(
        assessment: AthleteAssessment,
        status: AdaptationStatus,
        source_reasons: tuple[AthleteAssessmentReason, ...],
    ) -> AdaptationDirective:

        return AdaptationDirective(
            as_of=assessment.as_of,
            status=status,
            source_reasons=source_reasons,
        )
