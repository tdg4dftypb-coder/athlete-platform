from decision.models import (
    DecisionState,
    WorkoutPlan,
)
from decision.rules.recovery import RecoveryRule


class DecisionEngine:

    def __init__(self) -> None:

        self.rules = [
            RecoveryRule(),
        ]

    def evaluate(
        self,
        state: DecisionState,
    ) -> WorkoutPlan:

        plan = WorkoutPlan()

        for rule in self.rules:
            result = rule.evaluate(state, plan)
            plan.add_result(result)

        return plan