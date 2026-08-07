"""Stateless serializers for TrainingPlan, FinalSessionPrescription, and read histories."""
from typing import Any

from training_plan.history import (
    FinalSessionPrescriptionHistory,
    TrainingPlanHistory,
)
from training_plan.models import PlannedSession, TrainingPlan
from training_plan.prescription import FinalSessionPrescription


class PlannedSessionSerializer:
    """Stateless serializer for PlannedSession."""

    def serialize(self, session: PlannedSession) -> dict[str, Any]:
        if not isinstance(session, PlannedSession):
            raise TypeError("session must be PlannedSession instance")

        return {
            "session_id": session.session_id,
            "date": session.date.isoformat(),
            "kind": session.kind.value,
            "session_type": session.session_type,
            "duration_minutes": session.duration_minutes,
            "target_tss": session.target_tss,
            "intensity": session.intensity,
            "priority": session.priority,
            "rationale": list(session.rationale),
        }


class TrainingPlanSerializer:
    """Stateless serializer for TrainingPlan."""

    def __init__(self) -> None:
        self._session_serializer = PlannedSessionSerializer()

    def serialize(self, plan: TrainingPlan) -> dict[str, Any]:
        if not isinstance(plan, TrainingPlan):
            raise TypeError("plan must be TrainingPlan instance")

        return {
            "plan_id": plan.plan_id,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "version": plan.version,
            "generated_at": plan.generated_at.isoformat(),
            "supersedes_plan_id": plan.supersedes_plan_id,
            "sessions": [self._session_serializer.serialize(s) for s in plan.sessions],
        }


class FinalSessionPrescriptionSerializer:
    """Stateless serializer for FinalSessionPrescription."""

    def __init__(self) -> None:
        self._session_serializer = PlannedSessionSerializer()

    def serialize(self, prescription: FinalSessionPrescription) -> dict[str, Any]:
        if not isinstance(prescription, FinalSessionPrescription):
            raise TypeError("prescription must be FinalSessionPrescription instance")

        return {
            "prescription_id": prescription.prescription_id,
            "plan_id": prescription.plan_id,
            "decision_id": prescription.decision_id,
            "date": prescription.date.isoformat(),
            "source_session": self._session_serializer.serialize(prescription.source_session),
            "disposition": prescription.disposition.value,
            "prescribed_kind": prescription.prescribed_kind.value if prescription.prescribed_kind else None,
            "prescribed_session_type": prescription.prescribed_session_type,
            "prescribed_duration_minutes": prescription.prescribed_duration_minutes,
            "prescribed_target_tss": prescription.prescribed_target_tss,
            "prescribed_intensity": prescription.prescribed_intensity,
            "reason_codes": list(prescription.reason_codes),
            "generated_at": prescription.generated_at.isoformat(),
            "reconciliation_policy_version": prescription.reconciliation_policy_version,
        }


class TrainingPlanHistorySerializer:
    """Stateless serializer for TrainingPlanHistory."""

    def __init__(self) -> None:
        self._plan_serializer = TrainingPlanSerializer()

    def serialize(self, history: TrainingPlanHistory) -> dict[str, Any]:
        if not isinstance(history, TrainingPlanHistory):
            raise TypeError("history must be TrainingPlanHistory instance")

        return {
            "records": [self._plan_serializer.serialize(r) for r in history.records],
            "count": history.count,
        }


class FinalSessionPrescriptionHistorySerializer:
    """Stateless serializer for FinalSessionPrescriptionHistory."""

    def __init__(self) -> None:
        self._prescription_serializer = FinalSessionPrescriptionSerializer()

    def serialize(self, history: FinalSessionPrescriptionHistory) -> dict[str, Any]:
        if not isinstance(history, FinalSessionPrescriptionHistory):
            raise TypeError("history must be FinalSessionPrescriptionHistory instance")

        return {
            "records": [self._prescription_serializer.serialize(r) for r in history.records],
            "count": history.count,
        }
