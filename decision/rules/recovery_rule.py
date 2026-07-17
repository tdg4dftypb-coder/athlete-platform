from athlete.models import AthleteState
from decision.models import DecisionState

from .base import DecisionRule


class RecoveryRule(DecisionRule):

    def matches(
        self,
        athlete: AthleteState,
    ) -> bool:

        return athlete.recovery.score < 60

    def decide(
        self,
        athlete: AthleteState,
    ) -> DecisionState:

        score = athlete.recovery.score

        if score < 40:

            return DecisionState(

                recommendation="REST",

                duration=0,

                target_tss=0,

                intensity="REST",

                reasons=[
                    f"Recovery {score}/100",
                ],

                priority=10,

                confidence=100.0,

                source_rules=[
                    self.__class__.__name__,
                ],

            )

        return DecisionState(

            recommendation="RECOVERY",

            duration=45,

            target_tss=25,

            intensity="Z1",

            reasons=[
                f"Recovery {score}/100",
            ],

            priority=20,

            confidence=100.0,

            source_rules=[
                self.__class__.__name__,
            ],

        )