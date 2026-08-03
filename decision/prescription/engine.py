from application.adaptation import AdaptationDirective, AdaptationStatus
from athlete.intelligence.models import AthleteInsight, AthleteInsightType
from decision.diagnosis.models import (
    AthleteDiagnosis,
    Readiness,
    RiskLevel,
)

from decision.prescription.models import (
    DecisionReason,
    TrainingObjective,
    TrainingPrescription,
)

class PrescriptionEngine:

    _INSIGHT_REASON_ORDER = (
        (
            AthleteInsightType.NEED_MORE_RECOVERY,
            DecisionReason.INSIGHT_NEED_MORE_RECOVERY,
        ),
        (
            AthleteInsightType.FATIGUE_ACCUMULATING,
            DecisionReason.INSIGHT_FATIGUE_ACCUMULATING,
        ),
        (
            AthleteInsightType.HIGH_TRAINING_COMPLIANCE,
            DecisionReason.INSIGHT_HIGH_TRAINING_COMPLIANCE,
        ),
    )

    _RESTRICTIVE_INSIGHT_TYPES = frozenset(
        {
            AthleteInsightType.NEED_MORE_RECOVERY,
            AthleteInsightType.FATIGUE_ACCUMULATING,
        }
    )

    def prescribe(
        self,
        diagnosis: AthleteDiagnosis,
        adaptation: AdaptationDirective | None = None,
        insights: tuple[AthleteInsight, ...] = (),
    ) -> TrainingPrescription:

        insight_types = frozenset(insight.type for insight in insights)
        decision_reasons = self._decision_reasons(adaptation, insight_types)

        #
        # Safety first
        #

        if (
            diagnosis.injury_risk == RiskLevel.HIGH
            or (
                adaptation is not None
                and adaptation.status is AdaptationStatus.REDUCE_LOAD
            )
        ):

            objective = TrainingObjective.RECOVERY

            duration = 45

            tss = 30

            priority = 100


        #
        # Ready intelligence constraints
        #

        elif insight_types & self._RESTRICTIVE_INSIGHT_TYPES:

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
            decision_reasons=decision_reasons,
        )

    @classmethod
    def _decision_reasons(
        cls,
        adaptation: AdaptationDirective | None,
        insight_types: frozenset[AthleteInsightType],
    ) -> tuple[DecisionReason, ...]:
        reasons = []

        if (
            adaptation is not None
            and adaptation.status is AdaptationStatus.REDUCE_LOAD
        ):
            reasons.append(DecisionReason.ADAPTATION_REDUCE_LOAD)

        reasons.extend(
            reason
            for insight_type, reason in cls._INSIGHT_REASON_ORDER
            if insight_type in insight_types
        )

        return tuple(reasons)
