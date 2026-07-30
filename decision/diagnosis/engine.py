from athlete.models import AthleteState

from decision.diagnosis.models import (
    AthleteDiagnosis,
    Readiness,
    RiskLevel,
)


class DiagnosisEngine:

    def analyze(
        self,
        athlete: AthleteState,
    ) -> AthleteDiagnosis:

        recovery = athlete.recovery.score

        fatigue = athlete.performance.fatigue

        fitness = athlete.performance.fitness

        freshness = athlete.performance.freshness


        #
        # Readiness
        #

        if (
            recovery >= 85
            and freshness >= 70
        ):

            readiness = Readiness.PEAK

            capacity = Readiness.HIGH

            risk = RiskLevel.LOW


        elif (
            recovery >= 70
            and fatigue <= 40
        ):

            readiness = Readiness.HIGH

            capacity = Readiness.HIGH

            risk = RiskLevel.LOW


        elif recovery >= 50:

            readiness = Readiness.MODERATE

            capacity = Readiness.MODERATE

            risk = RiskLevel.MODERATE


        else:

            readiness = Readiness.LOW

            capacity = Readiness.LOW

            risk = RiskLevel.HIGH


        #
        # Fatigue override
        #

        if fatigue >= 80:

            readiness = Readiness.LOW

            capacity = Readiness.LOW

            risk = RiskLevel.HIGH


        #
        # Capacity uses fitness only when meaningful
        #

        if fitness >= 80:

            capacity = Readiness.HIGH


        #
        # Reasons
        #

        reasons = list(
            athlete.recovery.reasons,
        )


        if fatigue >= 70:

            reasons.append(
                "High fatigue",
            )


        if freshness >= 70:

            reasons.append(
                "High freshness",
            )


        if fitness >= 80:

            reasons.append(
                "High fitness",
            )


        return AthleteDiagnosis(

            readiness=readiness,

            training_capacity=capacity,

            injury_risk=risk,

            confidence=100,

            reasons=reasons,

        )