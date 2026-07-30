from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from application.knowledge_context import AthleteKnowledgeContext
from athlete.memory.models import DateRange, TrainingPattern


class TrainingAssessmentStatus(Enum):
    NO_TRAINING_DATA = "no_training_data"
    NO_CLEAR_PATTERN = "no_clear_pattern"
    CONSISTENT_EXECUTION = "consistent_execution"
    ATTENTION_REQUIRED = "attention_required"


@dataclass(frozen=True)
class TrainingAssessment:
    as_of: datetime
    period: DateRange | None
    status: TrainingAssessmentStatus
    supporting_patterns: tuple[TrainingPattern, ...]


class TrainingAssessmentBuilder:
    """Interprets the typed training facts already present in a knowledge context."""

    WARNING_PATTERN_CODES = frozenset(
        {
            "REPEATED_PARTIAL_EXECUTION",
            "REPEATED_UNDER_EXECUTION",
            "REPEATED_OVER_EXECUTION",
        }
    )
    CONSISTENT_EXECUTION_CODE = "CONSISTENT_EXECUTION"

    def build(
        self,
        context: AthleteKnowledgeContext,
    ) -> TrainingAssessment:

        review = context.weekly_review

        if review is None:
            return self._assessment(
                context,
                period=None,
                status=TrainingAssessmentStatus.NO_TRAINING_DATA,
                supporting_patterns=(),
            )

        if review.trends.workouts_count == 0:
            return self._assessment(
                context,
                period=review.period,
                status=TrainingAssessmentStatus.NO_TRAINING_DATA,
                supporting_patterns=(),
            )

        warning_patterns = tuple(
            pattern
            for pattern in review.patterns.patterns
            if pattern.code in self.WARNING_PATTERN_CODES
        )
        if warning_patterns:
            return self._assessment(
                context,
                period=review.period,
                status=TrainingAssessmentStatus.ATTENTION_REQUIRED,
                supporting_patterns=warning_patterns,
            )

        consistent_patterns = tuple(
            pattern
            for pattern in review.patterns.patterns
            if pattern.code == self.CONSISTENT_EXECUTION_CODE
        )
        if consistent_patterns:
            return self._assessment(
                context,
                period=review.period,
                status=TrainingAssessmentStatus.CONSISTENT_EXECUTION,
                supporting_patterns=consistent_patterns,
            )

        return self._assessment(
            context,
            period=review.period,
            status=TrainingAssessmentStatus.NO_CLEAR_PATTERN,
            supporting_patterns=(),
        )

    @staticmethod
    def _assessment(
        context: AthleteKnowledgeContext,
        *,
        period: DateRange | None,
        status: TrainingAssessmentStatus,
        supporting_patterns: tuple[TrainingPattern, ...],
    ) -> TrainingAssessment:

        return TrainingAssessment(
            as_of=context.as_of,
            period=period,
            status=status,
            supporting_patterns=supporting_patterns,
        )
