from dataclasses import dataclass

from athlete.memory.models import DateRange, PatternReport, TrainingTrendReport


class ReviewPeriodMismatchError(ValueError):
    """Raised when reports for different periods are composed into a review."""


@dataclass(frozen=True)
class WeeklyTrainingReview:
    period: DateRange
    trends: TrainingTrendReport
    patterns: PatternReport
    source_event_ids: tuple[str, ...]
