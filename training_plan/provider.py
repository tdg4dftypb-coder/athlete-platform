"""Repository-backed implementation of TrainingPlanProvider."""
from datetime import date
from typing import Optional

from training_plan.models import PlannedSession, TrainingPlan
from training_plan.ports import TrainingPlanProvider
from training_plan.repository import TrainingPlanRepository, TrainingPlanRepositoryError
from training_plan.selector import MultiplePlannedSessionsError, TrainingPlanSessionSelector


class RepositoryTrainingPlanProvider(TrainingPlanProvider):
    """Read-only TrainingPlanProvider backed by a TrainingPlanRepository."""

    def __init__(self, repository: TrainingPlanRepository) -> None:
        if repository is None:
            raise TypeError("repository must not be None")
        self._repository = repository
        self._selector = TrainingPlanSessionSelector()

    def get_plan_for_date(self, target_date: date) -> Optional[TrainingPlan]:
        if type(target_date) is not date:
            raise TypeError("target_date must be date instance (not datetime)")
        try:
            return self._repository.get_for_date(target_date)
        except TrainingPlanRepositoryError:
            return None

    def get_planned_session(self, target_date: date) -> Optional[PlannedSession]:
        sessions = self.get_planned_sessions(target_date)
        if not sessions:
            return None
        if len(sessions) > 1:
            raise MultiplePlannedSessionsError(
                f"date {target_date} contains {len(sessions)} planned sessions; "
                "use get_planned_sessions()"
            )
        return sessions[0]

    def get_planned_sessions(
        self, target_date: date
    ) -> tuple[PlannedSession, ...]:
        if type(target_date) is not date:
            raise TypeError("target_date must be date instance (not datetime)")
        plan = self.get_plan_for_date(target_date)
        if plan is None:
            return ()
        return self._selector.get_all_for_date(plan, target_date)
