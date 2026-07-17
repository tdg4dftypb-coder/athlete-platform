from decision.models import (
    DecisionState,
    RuleResult,
    WorkoutPlan,
)
from decision.rules.base import Rule
from workout.enums import WorkoutType


class RecoveryRule(Rule):

    def evaluate(
        self,
        state: DecisionState,
        plan: WorkoutPlan,
    ) -> RuleResult:

        if state.recovery < 30:
            return RuleResult(
                source=self.__class__.__name__,
                scores={
                    WorkoutType.RECOVERY: 100.0,
                },
                reason="Recovery < 30",
            )

        if state.recovery < 50:
            return RuleResult(
                source=self.__class__.__name__,
                scores={
                    WorkoutType.ENDURANCE: 30.0,
                },
                reason="Recovery < 50",
            )

        return RuleResult(
            source=self.__class__.__name__,
            scores={
                WorkoutType.TEMPO: 10.0,
            },
            reason="Recovery OK",
        )