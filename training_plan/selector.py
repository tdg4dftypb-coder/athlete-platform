"""Stateless selection helper for TrainingPlan sessions."""
from datetime import date
from typing import Optional

from training_plan.models import PlannedSession, TrainingPlan


class TrainingPlanSessionSelector:
    """Helper service to resolve PlannedSession for a given date from a TrainingPlan."""

    def get_for_date(self, plan: TrainingPlan, target_date: date) -> Optional[PlannedSession]:
        """Resolves PlannedSession for target_date if within plan range, else returns None."""
        if not isinstance(plan, TrainingPlan):
            raise TypeError("plan must be TrainingPlan instance")
        if type(target_date) is not date:
            raise TypeError("target_date must be date instance")

        if target_date < plan.start_date or target_date > plan.end_date:
            return None

        # Calculate exact zero-based index in gapless chronological array
        idx = (target_date - plan.start_date).days
        if 0 <= idx < len(plan.sessions):
            session = plan.sessions[idx]
            if session.date == target_date:
                return session

        # Fallback binary search or filter if order was guaranteed
        for s in plan.sessions:
            if s.date == target_date:
                return s

        return None
