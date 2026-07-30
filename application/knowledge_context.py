from dataclasses import dataclass
from datetime import datetime

from athlete.models import AthleteState
from athlete.review.models import WeeklyTrainingReview


@dataclass(frozen=True)
class AthleteKnowledgeContext:
    as_of: datetime
    athlete_state: AthleteState | None
    weekly_review: WeeklyTrainingReview | None


class AthleteKnowledgeContextBuilder:
    """Composes already prepared athlete facts into an application context."""

    def build(
        self,
        *,
        as_of: datetime,
        athlete_state: AthleteState | None = None,
        weekly_review: WeeklyTrainingReview | None = None,
    ) -> AthleteKnowledgeContext:

        return AthleteKnowledgeContext(
            as_of=as_of,
            athlete_state=athlete_state,
            weekly_review=weekly_review,
        )
