from athlete.models import AthleteState
from decision.models import DecisionState

from .base import DecisionRule


class FatigueRule(DecisionRule):

    def matches(
        self,
        athlete: AthleteState,
    ) -> bool:

        return athlete.performance.tsb < -25

    def decide(
        self,
        athlete: AthleteState,
    ) -> DecisionState:

        return DecisionState(

            recommendation="ENDURANCE",

            duration=90,

            target_tss=55,

            intensity="Z2",

            reasons=[
                f"TSB {athlete.performance.tsb:.1f}"
            ],

            priority=20,

            confidence=95.0,

            source_rules=[
                self.__class__.__name__
            ],

        )