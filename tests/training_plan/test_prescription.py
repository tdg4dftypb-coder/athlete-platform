"""Unit tests for PrescriptionDisposition and FinalSessionPrescription domain models."""
from datetime import date, datetime, timezone
import pytest

from training_plan.models import PlannedSession, PlannedSessionKind
from training_plan.prescription import (
    FinalSessionPrescription,
    PrescriptionDisposition,
)


def test_prescription_disposition_enum_values():
    assert PrescriptionDisposition.AS_PLANNED.value == "AS_PLANNED"
    assert PrescriptionDisposition.REDUCED.value == "REDUCED"
    assert PrescriptionDisposition.RECOVERY_REPLACEMENT.value == "RECOVERY_REPLACEMENT"
    assert PrescriptionDisposition.REST.value == "REST"
    assert PrescriptionDisposition.HOLD_FOR_REVIEW.value == "HOLD_FOR_REVIEW"


def test_valid_as_planned_prescription():
    src = PlannedSession(
        session_id="s1",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="VO2",
        duration_minutes=60,
        target_tss=75.0,
        intensity="HIGH",
        priority=4,
        rationale=("Intervals",),
    )
    t_gen = datetime(2026, 8, 10, 7, 0, 0, tzinfo=timezone.utc)

    rx = FinalSessionPrescription(
        prescription_id="s1:dec-123",
        plan_id="plan-1",
        decision_id="dec-123",
        source_session=src,
        disposition=PrescriptionDisposition.AS_PLANNED,
        prescribed_kind=PlannedSessionKind.TRAINING,
        prescribed_session_type="VO2",
        prescribed_duration_minutes=60,
        prescribed_target_tss=75.0,
        prescribed_intensity="HIGH",
        reason_codes=("SIG_PROCEED",),
        generated_at=t_gen,
    )

    assert rx.prescription_id == "s1:dec-123"
    assert rx.date == date(2026, 8, 10)
    assert rx.disposition == PrescriptionDisposition.AS_PLANNED
    assert rx.prescribed_session_type == "VO2"
    assert rx.reconciliation_policy_version == "1.0"


def test_hold_for_review_invariants():
    src = PlannedSession(
        session_id="s1",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="THRESHOLD",
        duration_minutes=75,
        target_tss=80.0,
        intensity="HIGH",
        priority=4,
        rationale=("FTP",),
    )
    t_gen = datetime(2026, 8, 10, 7, 0, 0, tzinfo=timezone.utc)

    rx = FinalSessionPrescription(
        prescription_id="s1:dec-review",
        plan_id="plan-1",
        decision_id="dec-review",
        source_session=src,
        disposition=PrescriptionDisposition.HOLD_FOR_REVIEW,
        prescribed_kind=None,
        prescribed_session_type=None,
        prescribed_duration_minutes=None,
        prescribed_target_tss=None,
        prescribed_intensity=None,
        reason_codes=("SIG_BIO_CRITICAL",),
        generated_at=t_gen,
    )

    assert rx.disposition == PrescriptionDisposition.HOLD_FOR_REVIEW
    assert rx.prescribed_kind is None
    assert rx.prescribed_duration_minutes is None

    # Invalid: HOLD_FOR_REVIEW with non-None duration/kind
    with pytest.raises(ValueError, match="HOLD_FOR_REVIEW prescribed_kind must be None"):
        FinalSessionPrescription(
            prescription_id="s1:dec-review",
            plan_id="plan-1",
            decision_id="dec-review",
            source_session=src,
            disposition=PrescriptionDisposition.HOLD_FOR_REVIEW,
            prescribed_kind=PlannedSessionKind.TRAINING,
            prescribed_session_type="THRESHOLD",
            prescribed_duration_minutes=75,
            prescribed_target_tss=80.0,
            prescribed_intensity="HIGH",
            reason_codes=("SIG_BIO_CRITICAL",),
            generated_at=t_gen,
        )


def test_rest_disposition_invariants():
    src = PlannedSession(
        session_id="s1",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="VO2",
        duration_minutes=60,
        target_tss=75.0,
        intensity="HIGH",
        priority=4,
        rationale=("Intervals",),
    )
    t_gen = datetime(2026, 8, 10, 7, 0, 0, tzinfo=timezone.utc)

    rx = FinalSessionPrescription(
        prescription_id="s1:dec-rest",
        plan_id="plan-1",
        decision_id="dec-rest",
        source_session=src,
        disposition=PrescriptionDisposition.REST,
        prescribed_kind=PlannedSessionKind.REST,
        prescribed_session_type=None,
        prescribed_duration_minutes=0,
        prescribed_target_tss=0.0,
        prescribed_intensity=None,
        reason_codes=("SIG_REC_CRITICAL",),
        generated_at=t_gen,
    )

    assert rx.disposition == PrescriptionDisposition.REST
    assert rx.prescribed_kind == PlannedSessionKind.REST
    assert rx.prescribed_duration_minutes == 0
    assert rx.prescribed_target_tss == 0.0
