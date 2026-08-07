"""Application-layer service for reconciling PlannedSession with persisted DecisionAuditRecord."""
from __future__ import annotations

from decision.history_v2 import DecisionAuditRecord
from decision.policy_v2 import DecisionAction
from training_plan.models import PlannedSession, PlannedSessionKind
from training_plan.prescription import (
    FinalSessionPrescription,
    PrescriptionDisposition,
)


class DailyTrainingReconciler:
    """Stateless reconciler mapping DecisionAuditRecord action to FinalSessionPrescription overlay."""

    REDUCTION_FACTOR: float = 0.70
    POLICY_VERSION: str = "1.0"

    def reconcile(
        self,
        plan_id: str,
        planned_session: PlannedSession,
        decision_record: DecisionAuditRecord,
    ) -> FinalSessionPrescription:
        """Reconciles a planned session with a persisted decision record.

        Guarantees:
        - Baseline PlannedSession is never mutated.
        - Deterministic prescription_id: {planned_session_id}:{decision_id}
        - Stable generated_at from decision_record.recorded_at
        - Reason codes copied directly from decision_record.policy_result.signals
        - Explicit REST days are never escalated to TRAINING.
        """
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise ValueError("plan_id must be non-empty string")

        if not isinstance(planned_session, PlannedSession):
            raise TypeError("planned_session must be PlannedSession instance")

        if not isinstance(decision_record, DecisionAuditRecord):
            raise TypeError("decision_record must be DecisionAuditRecord instance")

        prescription_id = f"{planned_session.session_id}:{decision_record.decision_id}"
        generated_at = decision_record.recorded_at

        # Copy signal codes deterministically
        if hasattr(decision_record.policy_result, "signals") and decision_record.policy_result.signals:
            reason_codes = tuple(sig.code for sig in decision_record.policy_result.signals)
        else:
            reason_codes = ()

        action = decision_record.policy_result.action

        # Safety rule: Explicit REST non-escalation
        if planned_session.kind == PlannedSessionKind.REST:
            if action == DecisionAction.REVIEW:
                return FinalSessionPrescription(
                    prescription_id=prescription_id,
                    plan_id=plan_id,
                    decision_id=decision_record.decision_id,
                    source_session=planned_session,
                    disposition=PrescriptionDisposition.HOLD_FOR_REVIEW,
                    prescribed_kind=None,
                    prescribed_session_type=None,
                    prescribed_duration_minutes=None,
                    prescribed_target_tss=None,
                    prescribed_intensity=None,
                    reason_codes=reason_codes,
                    generated_at=generated_at,
                    reconciliation_policy_version=self.POLICY_VERSION,
                )
            disposition = (
                PrescriptionDisposition.AS_PLANNED
                if action == DecisionAction.PROCEED
                else PrescriptionDisposition.REST
            )
            return FinalSessionPrescription(
                prescription_id=prescription_id,
                plan_id=plan_id,
                decision_id=decision_record.decision_id,
                source_session=planned_session,
                disposition=disposition,
                prescribed_kind=PlannedSessionKind.REST,
                prescribed_session_type=None,
                prescribed_duration_minutes=0,
                prescribed_target_tss=0.0,
                prescribed_intensity=None,
                reason_codes=reason_codes,
                generated_at=generated_at,
                reconciliation_policy_version=self.POLICY_VERSION,
            )

        # Source is TRAINING session
        if action == DecisionAction.PROCEED:
            return FinalSessionPrescription(
                prescription_id=prescription_id,
                plan_id=plan_id,
                decision_id=decision_record.decision_id,
                source_session=planned_session,
                disposition=PrescriptionDisposition.AS_PLANNED,
                prescribed_kind=PlannedSessionKind.TRAINING,
                prescribed_session_type=planned_session.session_type,
                prescribed_duration_minutes=planned_session.duration_minutes,
                prescribed_target_tss=planned_session.target_tss,
                prescribed_intensity=planned_session.intensity,
                reason_codes=reason_codes,
                generated_at=generated_at,
                reconciliation_policy_version=self.POLICY_VERSION,
            )

        if action == DecisionAction.REDUCE:
            reduced_duration = max(1, int(planned_session.duration_minutes * self.REDUCTION_FACTOR))
            reduced_tss = (
                planned_session.target_tss * self.REDUCTION_FACTOR
                if planned_session.target_tss is not None
                else None
            )
            return FinalSessionPrescription(
                prescription_id=prescription_id,
                plan_id=plan_id,
                decision_id=decision_record.decision_id,
                source_session=planned_session,
                disposition=PrescriptionDisposition.REDUCED,
                prescribed_kind=PlannedSessionKind.TRAINING,
                prescribed_session_type=planned_session.session_type,
                prescribed_duration_minutes=reduced_duration,
                prescribed_target_tss=reduced_tss,
                prescribed_intensity=planned_session.intensity,
                reason_codes=reason_codes,
                generated_at=generated_at,
                reconciliation_policy_version=self.POLICY_VERSION,
            )

        if action == DecisionAction.REPLACE_WITH_RECOVERY:
            rec_duration = min(planned_session.duration_minutes, 45)
            return FinalSessionPrescription(
                prescription_id=prescription_id,
                plan_id=plan_id,
                decision_id=decision_record.decision_id,
                source_session=planned_session,
                disposition=PrescriptionDisposition.RECOVERY_REPLACEMENT,
                prescribed_kind=PlannedSessionKind.TRAINING,
                prescribed_session_type="RECOVERY",
                prescribed_duration_minutes=rec_duration,
                prescribed_target_tss=None,
                prescribed_intensity="LOW",
                reason_codes=reason_codes,
                generated_at=generated_at,
                reconciliation_policy_version=self.POLICY_VERSION,
            )

        if action == DecisionAction.REST:
            return FinalSessionPrescription(
                prescription_id=prescription_id,
                plan_id=plan_id,
                decision_id=decision_record.decision_id,
                source_session=planned_session,
                disposition=PrescriptionDisposition.REST,
                prescribed_kind=PlannedSessionKind.REST,
                prescribed_session_type=None,
                prescribed_duration_minutes=0,
                prescribed_target_tss=0.0,
                prescribed_intensity=None,
                reason_codes=reason_codes,
                generated_at=generated_at,
                reconciliation_policy_version=self.POLICY_VERSION,
            )

        if action == DecisionAction.REVIEW:
            return FinalSessionPrescription(
                prescription_id=prescription_id,
                plan_id=plan_id,
                decision_id=decision_record.decision_id,
                source_session=planned_session,
                disposition=PrescriptionDisposition.HOLD_FOR_REVIEW,
                prescribed_kind=None,
                prescribed_session_type=None,
                prescribed_duration_minutes=None,
                prescribed_target_tss=None,
                prescribed_intensity=None,
                reason_codes=reason_codes,
                generated_at=generated_at,
                reconciliation_policy_version=self.POLICY_VERSION,
            )

        raise ValueError(f"Unsupported DecisionAction: {action}")
