"""Ports and Protocols for Training Plan Bounded Context."""
from datetime import date
from typing import Optional, Protocol, runtime_checkable

from training_plan.models import PlannedSession, TrainingPlan


@runtime_checkable
class TrainingPlanProvider(Protocol):
    """Abstract protocol for providing active training plan or daily planned session."""

    def get_plan_for_date(self, target_date: date) -> Optional[TrainingPlan]:
        """Returns the TrainingPlan applicable for a given target_date, or None if unavailable."""
        ...

    def get_planned_session(self, target_date: date) -> Optional[PlannedSession]:
        """Returns the PlannedSession for a given date, or None if unavailable."""
        ...
