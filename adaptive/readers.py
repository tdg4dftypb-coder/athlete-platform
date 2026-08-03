from dataclasses import dataclass
from datetime import date, datetime

from adaptive.goals import ActiveGoalSelector
from adaptive.models import AthleteGoal


@dataclass(frozen=True)
class InMemoryAthleteGoalReader:
    """Deterministic MVP goal source backed by immutable configuration."""

    goals: tuple[AthleteGoal, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.goals, tuple):
            raise TypeError("goals must be a tuple")

    def load_active_goal(
        self,
        *,
        valid_for_date: date,
        as_of: datetime,
    ) -> AthleteGoal | None:
        return ActiveGoalSelector().select(
            self.goals,
            valid_for_date=valid_for_date,
            as_of=as_of,
        )
