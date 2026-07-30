from athlete.memory.models import PatternReport, TrainingTrendReport
from athlete.review.models import ReviewPeriodMismatchError, WeeklyTrainingReview


class WeeklyReviewService:
    """Composes existing training reports into a deterministic weekly review."""

    def build(
        self,
        trends: TrainingTrendReport,
        patterns: PatternReport,
    ) -> WeeklyTrainingReview:

        if trends.period != patterns.period:
            raise ReviewPeriodMismatchError(
                "Training trends period "
                f"{trends.period!r} does not match patterns period "
                f"{patterns.period!r}"
            )

        return WeeklyTrainingReview(
            period=trends.period,
            trends=trends,
            patterns=patterns,
            source_event_ids=patterns.source_event_ids,
        )
