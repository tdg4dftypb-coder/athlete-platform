"""Ports and Protocols for Training Plan Bounded Context."""
from datetime import date
from typing import Optional, Protocol, runtime_checkable

from training_plan.models import PlannedSession, TrainingPlan


@runtime_checkable
class TrainingPlanProvider(Protocol):
    """Provide an active plan and its daily atomic planned sessions."""

    def get_plan_for_date(self, target_date: date) -> Optional[TrainingPlan]:
        """Returns the TrainingPlan applicable for a given target_date, or None if unavailable."""
        ...

    def get_planned_sessions(
        self, target_date: date
    ) -> tuple[PlannedSession, ...]:
        """Returns all sessions for a date in canonical order, or an empty tuple."""
        ...

    def get_planned_session(self, target_date: date) -> Optional[PlannedSession]:
        """Bounded compatibility operation for a date with at most one session."""
        ...
