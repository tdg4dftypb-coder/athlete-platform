"""Prescription models for the daily adaptive reconciliation overlay."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from training_plan.models import PlannedSession, PlannedSessionKind


class PrescriptionDisposition(Enum):
    """Domain output disposition for daily adapted session prescription."""
    AS_PLANNED = "AS_PLANNED"
    REDUCED = "REDUCED"
    RECOVERY_REPLACEMENT = "RECOVERY_REPLACEMENT"
    REST = "REST"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW"


@dataclass(frozen=True)
class FinalSessionPrescription:
    """Immutable prescription for one atomic source PlannedSession."""

    prescription_id: str
    plan_id: str
    decision_id: str
    source_session: PlannedSession
    disposition: PrescriptionDisposition
    prescribed_kind: PlannedSessionKind | None
    prescribed_session_type: str | None
    prescribed_duration_minutes: int | None
    prescribed_target_tss: float | None
    prescribed_intensity: str | None
    reason_codes: tuple[str, ...]
    generated_at: datetime
    reconciliation_policy_version: str = "1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.prescription_id, str) or not self.prescription_id.strip():
            raise ValueError("prescription_id must be non-empty string")

        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("plan_id must be non-empty string")

        if not isinstance(self.decision_id, str) or not self.decision_id.strip():
            raise ValueError("decision_id must be non-empty string")

        if not isinstance(self.source_session, PlannedSession):
            raise TypeError("source_session must be PlannedSession instance")

        if not isinstance(self.disposition, PrescriptionDisposition):
            raise TypeError("disposition must be PrescriptionDisposition instance")

        if not isinstance(self.reason_codes, tuple):
            raise TypeError("reason_codes must be tuple")
        for item in self.reason_codes:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("reason_codes items must be non-empty strings")

        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be datetime instance")

        if not isinstance(self.reconciliation_policy_version, str) or not self.reconciliation_policy_version.strip():
            raise ValueError("reconciliation_policy_version must be non-empty string")

        # Disposition-specific invariants
        if self.disposition == PrescriptionDisposition.HOLD_FOR_REVIEW:
            if self.prescribed_kind is not None:
                raise ValueError("HOLD_FOR_REVIEW prescribed_kind must be None")
            if self.prescribed_session_type is not None:
                raise ValueError("HOLD_FOR_REVIEW prescribed_session_type must be None")
            if self.prescribed_duration_minutes is not None:
                raise ValueError("HOLD_FOR_REVIEW prescribed_duration_minutes must be None")
            if self.prescribed_target_tss is not None:
                raise ValueError("HOLD_FOR_REVIEW prescribed_target_tss must be None")
            if self.prescribed_intensity is not None:
                raise ValueError("HOLD_FOR_REVIEW prescribed_intensity must be None")

        elif self.disposition == PrescriptionDisposition.REST:
            if self.prescribed_kind != PlannedSessionKind.REST:
                raise ValueError("REST disposition prescribed_kind must be PlannedSessionKind.REST")
            if self.prescribed_session_type is not None:
                raise ValueError("REST disposition prescribed_session_type must be None")
            if self.prescribed_duration_minutes != 0:
                raise ValueError("REST disposition prescribed_duration_minutes must be 0")
            if self.prescribed_target_tss != 0.0:
                raise ValueError("REST disposition prescribed_target_tss must be 0.0")
            if self.prescribed_intensity is not None:
                raise ValueError("REST disposition prescribed_intensity must be None")

        elif self.disposition in (
            PrescriptionDisposition.AS_PLANNED,
            PrescriptionDisposition.REDUCED,
            PrescriptionDisposition.RECOVERY_REPLACEMENT,
        ):
            if self.prescribed_kind == PlannedSessionKind.REST:
                if self.prescribed_session_type is not None:
                    raise ValueError("REST prescribed_session_type must be None")
                if self.prescribed_duration_minutes != 0:
                    raise ValueError("REST prescribed_duration_minutes must be 0")
                if self.prescribed_target_tss != 0.0:
                    raise ValueError("REST prescribed_target_tss must be 0.0")
                if self.prescribed_intensity is not None:
                    raise ValueError("REST prescribed_intensity must be None")
            elif self.prescribed_kind == PlannedSessionKind.TRAINING:
                if not isinstance(self.prescribed_session_type, str) or not self.prescribed_session_type.strip():
                    raise ValueError("TRAINING prescribed_session_type must be non-empty string")
                object.__setattr__(self, "prescribed_session_type", self.prescribed_session_type.strip().upper())

                if not isinstance(self.prescribed_duration_minutes, int) or self.prescribed_duration_minutes <= 0:
                    raise ValueError("TRAINING prescribed_duration_minutes must be int > 0")

                if self.prescribed_target_tss is not None:
                    if not isinstance(self.prescribed_target_tss, (int, float)) or self.prescribed_target_tss < 0.0:
                        raise ValueError("prescribed_target_tss must be float or int >= 0.0")

                if self.prescribed_intensity is not None:
                    if not isinstance(self.prescribed_intensity, str) or not self.prescribed_intensity.strip():
                        raise ValueError("prescribed_intensity must be non-empty string if provided")
                    object.__setattr__(self, "prescribed_intensity", self.prescribed_intensity.strip().upper())

    @property
    def date(self) -> date:
        """Convenience property delegating to the source session date."""
        return self.source_session.date
