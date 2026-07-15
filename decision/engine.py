from athlete.models import AthleteState
from decision.models import DecisionState


class DecisionEngine:

    def decide(
        self,
        athlete: AthleteState,
    ) -> DecisionState:

        performance = athlete.performance

        recovery = athlete.recovery

        reasons = []

        #
        # Recovery
        #

        if recovery.score < 60:

            reasons.append(
                f"Recovery {recovery.score}"
            )

            return DecisionState(

                recommendation="REST",

                duration=0,

                target_tss=0,

                intensity="REST",

                reasons=reasons,

            )

        #
        # Fatigue
        #

        if performance.tsb < -25:

            reasons.append(
                f"TSB {round(performance.tsb,1)}"
            )

            return DecisionState(

                recommendation="ENDURANCE",

                duration=90,

                target_tss=55,

                intensity="Z2",

                reasons=reasons,

            )

        #
        # Fresh
        #

        if performance.tsb > 10:

            reasons.append(
                f"TSB {round(performance.tsb,1)}"
            )

            return DecisionState(

                recommendation="VO2",

                duration=75,

                target_tss=95,

                intensity="VO2",

                reasons=reasons,

            )

        #
        # Default
        #

        reasons.append(
            "Balanced load"
        )

        return DecisionState(

            recommendation="TEMPO",

            duration=90,

            target_tss=70,

            intensity="Z3",

            reasons=reasons,

        )