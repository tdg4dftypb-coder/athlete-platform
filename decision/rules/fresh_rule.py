from athlete.models import AthleteState
from decision.models import DecisionState

from .base import DecisionRule


class FreshRule(DecisionRule):

    def matches(
        self,
        athlete: AthleteState,
    ) -> bool:

        return athlete.performance.tsb > 10

    def decide(
        self,
        athlete: AthleteState,
    ) -> DecisionState:

        return DecisionState(

            recommendation="VO2",

            duration=75,

            target_tss=95,

            intensity="VO2",

            reasons=[
                f"TSB {athlete.performance.tsb:.1f}"
            ],

            priority=30,

            confidence=95.0,

            source_rules=[
                self.__class__.__name__
            ],

        )