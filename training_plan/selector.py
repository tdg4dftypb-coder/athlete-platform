"""Stateless selection helper for TrainingPlan sessions."""
from datetime import date
from training_plan.models import PlannedSession, TrainingPlan


class MultiplePlannedSessionsError(ValueError):
    """The legacy single-session selector cannot represent a multi-session date."""


class TrainingPlanSessionSelector:
    """Resolve the canonically ordered planned sessions for a calendar date."""

    def get_all_for_date(
        self, plan: TrainingPlan, target_date: date
    ) -> tuple[PlannedSession, ...]:
        """Return every session for the date, or an empty tuple outside the plan."""
        if not isinstance(plan, TrainingPlan):
            raise TypeError("plan must be TrainingPlan instance")
        if type(target_date) is not date:
            raise TypeError("target_date must be date instance")

        if target_date < plan.start_date or target_date > plan.end_date:
            return ()
        return tuple(session for session in plan.sessions if session.date == target_date)

    def get_for_date(
        self, plan: TrainingPlan, target_date: date
    ) -> PlannedSession | None:
        """Compatibility selector for dates containing at most one session."""
        sessions = self.get_all_for_date(plan, target_date)
        if not sessions:
            return None
        if len(sessions) > 1:
            raise MultiplePlannedSessionsError(
                f"date {target_date} contains {len(sessions)} planned sessions; "
                "use get_all_for_date()"
            )
        return sessions[0]
