from abc import ABC, abstractmethod

from decision.models import (
    DecisionState,
    RuleResult,
    WorkoutPlan,
)


class Rule(ABC):

    @abstractmethod
    def evaluate(
        self,
        state: DecisionState,
        plan: WorkoutPlan,
    ) -> RuleResult:
        ...