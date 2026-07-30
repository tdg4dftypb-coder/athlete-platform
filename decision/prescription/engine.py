from decision.diagnosis.models import (
    AthleteDiagnosis,
    Readiness,
    RiskLevel,
)

from decision.prescription.models import (
    TrainingObjective,
    TrainingPrescription,
)


class PrescriptionEngine:

    def prescribe(
        self,
        diagnosis: AthleteDiagnosis,
    ) -> TrainingPrescription:


        #
        # Safety first
        #

        if diagnosis.injury_risk == RiskLevel.HIGH:

            objective = TrainingObjective.RECOVERY

            duration = 45

            tss = 30

            priority = 100


        #
        # Peak condition
        #

        elif (
            diagnosis.readiness == Readiness.PEAK
            and diagnosis.training_capacity == Readiness.HIGH
        ):

            objective = TrainingObjective.VO2

            duration = 60

            tss = 80

            priority = 100


        #
        # High readiness
        #

        elif (
            diagnosis.readiness == Readiness.HIGH
            and diagnosis.training_capacity == Readiness.HIGH
        ):

            objective = TrainingObjective.THRESHOLD

            duration = 75

            tss = 75

            priority = 90


        #
        # Moderate capacity
        #

        elif (
            diagnosis.readiness == Readiness.MODERATE
            and diagnosis.training_capacity
            in (
                Readiness.MODERATE,
                Readiness.HIGH,
            )
        ):

            objective = TrainingObjective.ENDURANCE

            duration = 90

            tss = 60

            priority = 70


        #
        # Low readiness
        #

        else:

            objective = TrainingObjective.RECOVERY

            duration = 45

            tss = 30

            priority = 100


        return TrainingPrescription(
            objective=objective,
            duration_minutes=duration,
            target_tss=tss,
            priority=priority,
            confidence=diagnosis.confidence,
            reasons=list(
                diagnosis.reasons,
            ),
        )