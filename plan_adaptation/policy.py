"""Stage 29.3 deterministic and conservative future-plan adaptation policy."""
from __future__ import annotations

from datetime import datetime

from application.athlete_assessment import (
    AthleteAssessmentReason,
    AthleteAssessmentStatus,
    FatigueStatus,
)
from training_plan.models import PlannedSessionKind
from training_plan.reduction import DURATION_REDUCTION_FACTOR_V1

from plan_adaptation.context import AdaptationContext
from plan_adaptation.models import (
    AdaptationAction,
    AdaptationEvaluationStatus,
    AdaptationReasonCode,
    AdaptationWarningCode,
    PlanAdaptationEvaluation,
    SessionAdaptationChange,
)


class DeterministicAdaptationPolicy:
    """Maps one immutable evidence context to one immutable evaluation.

    Policy v1 preserves the plan unless the canonical AthleteAssessment contains
    an explicit recovery/fatigue safety signal. The smallest safe intervention
    is applied to the nearest eligible future TRAINING session.
    """

    POLICY_VERSION = "1.0"
    REDUCTION_FACTOR = DURATION_REDUCTION_FACTOR_V1

    @property
    def policy_version(self) -> str:
        return self.POLICY_VERSION

    def evaluate(
        self,
        context: AdaptationContext,
        *,
        evaluated_at: datetime,
    ) -> PlanAdaptationEvaluation:
        if not isinstance(context, AdaptationContext):
            raise TypeError("context must be AdaptationContext")
        if not isinstance(evaluated_at, datetime):
            raise TypeError("evaluated_at must be datetime")

        changes, policy_warnings = self._recovery_protection_changes(context)
        status = (
            AdaptationEvaluationStatus.CHANGE_PROPOSED
            if changes
            else AdaptationEvaluationStatus.NO_CHANGE
        )
        reasons = (
            (AdaptationReasonCode.RECOVERY_PROTECTION,)
            if changes
            else ()
        )
        return PlanAdaptationEvaluation(
            adaptation_id=f"adaptation:{self.POLICY_VERSION}:{context.input_fingerprint}",
            policy_version=self.POLICY_VERSION,
            status=status,
            evaluation_date=context.evaluation_date,
            context_window=context.context_window,
            mutation_window=context.mutation_window,
            source_plan_id=context.source_plan_id,
            source_plan_version=context.source_plan_version,
            proposed_changes=changes,
            reason_codes=reasons,
            warning_codes=tuple({*context.warning_codes, *policy_warnings}),
            input_fingerprint=context.input_fingerprint,
            evaluated_at=evaluated_at,
        )

    def _recovery_protection_changes(
        self,
        context: AdaptationContext,
    ) -> tuple[
        tuple[SessionAdaptationChange, ...],
        tuple[AdaptationWarningCode, ...],
    ]:
        assessment = context.athlete_state
        if assessment is None or assessment.status is not AthleteAssessmentStatus.CAUTION:
            return (), ()

        explicit_safety_signal = (
            assessment.fatigue_status is FatigueStatus.HIGH
            or AthleteAssessmentReason.LOW_RECOVERY in assessment.reasons
            or AthleteAssessmentReason.HIGH_FATIGUE in assessment.reasons
        )
        if not explicit_safety_signal:
            return (), ()

        eligible = []
        for session in context.future_sessions:
            if session.kind is PlannedSessionKind.TRAINING:
                target_duration = max(1, int(session.duration_minutes * self.REDUCTION_FACTOR))
                if target_duration < session.duration_minutes:
                    eligible.append((session, target_duration))
        if not eligible:
            return (), ()

        nearest_date = eligible[0][0].date
        nearest = tuple(item for item in eligible if item[0].date == nearest_date)
        lowest_priority = min(session.priority for session, _ in nearest)
        candidates = tuple(
            item for item in nearest if item[0].priority == lowest_priority
        )
        if len(candidates) != 1:
            return (), (AdaptationWarningCode.AMBIGUOUS_ADAPTATION_TARGET,)

        session, target_duration = candidates[0]
        return (
            (
                SessionAdaptationChange(
                    session_id=session.session_id,
                    session_date=session.date,
                    action=AdaptationAction.SHORTEN,
                    reason_codes=(AdaptationReasonCode.RECOVERY_PROTECTION,),
                    target_duration_minutes=target_duration,
                ),
            ),
            (),
        )
