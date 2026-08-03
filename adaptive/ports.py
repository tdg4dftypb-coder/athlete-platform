from datetime import date, datetime
from typing import Protocol, runtime_checkable

from adaptive.models import AthleteGoal


@runtime_checkable
class AthleteGoalReader(Protocol):
    """Read the single active goal available for a deterministic date."""

    def load_active_goal(
        self,
        *,
        valid_for_date: date,
        as_of: datetime,
    ) -> AthleteGoal | None: ...
