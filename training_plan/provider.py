"""Repository-backed implementation of TrainingPlanProvider."""
from datetime import date
from typing import Optional

from training_plan.models import PlannedSession, TrainingPlan
from training_plan.ports import TrainingPlanProvider
from training_plan.repository import TrainingPlanRepository, TrainingPlanRepositoryError
from training_plan.selector import TrainingPlanSessionSelector


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
        if type(target_date) is not date:
            raise TypeError("target_date must be date instance (not datetime)")
        plan = self.get_plan_for_date(target_date)
        if plan is None:
            return None
        return self._selector.get_for_date(plan, target_date)
