"""Unit tests for DailyTrainingReconciler application service and reconciliation contracts."""
from datetime import date, datetime, timezone
import pytest

from application.training_plan_reconciliation import DailyTrainingReconciler
from decision.history_v2 import DecisionAuditRecord
from decision.policy_v2 import (
    DecisionAction,
    DecisionPolicyResult,
    DecisionPolicySignal,
    DecisionSeverity,
)
from training_plan.models import PlannedSession, PlannedSessionKind
from training_plan.prescription import PrescriptionDisposition


from decision.context import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    ContextDataStatus,
    PerformanceDecisionContext,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)
from decision.recommendation_plan import RecommendationPlanBuilder


def make_test_decision_record(
    decision_id: str,
    action: DecisionAction,
    signal_code: str = "SIG_TEST",
    recorded_at: datetime | None = None,
) -> DecisionAuditRecord:
    if recorded_at is None:
        recorded_at = datetime(2026, 8, 10, 7, 0, 0, tzinfo=timezone.utc)

    sig = DecisionPolicySignal(
        code=signal_code,
        source="test_source",
        severity=DecisionSeverity.MEDIUM,
        summary="Test signal summary",
    )

    result = DecisionPolicyResult(
        generated_at=recorded_at,
        action=action,
        severity=DecisionSeverity.MEDIUM,
        signals=(sig,),
        confidence=0.90,
        policy_version="2.0",
    )

    rec_ctx = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, generated_at=recorded_at)
    tr_ctx = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, generated_at=recorded_at)
    bio_ctx = BiomarkerDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        attention_count=0,
        critical_count=0,
        generated_at=recorded_at,
    )
    perf_ctx = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)

    context = AthleteDecisionContext(
        generated_at=recorded_at,
        recovery=rec_ctx,
        training=tr_ctx,
        biomarkers=bio_ctx,
        performance=perf_ctx,
    )

    rec_plan_builder = RecommendationPlanBuilder()
    plan = rec_plan_builder.build(result)

    return DecisionAuditRecord(
        decision_id=decision_id,
        recorded_at=recorded_at,
        context=context,
        policy_result=result,
        recommendation_plan=plan,
    )


def test_reconcile_training_proceed():
    reconciler = DailyTrainingReconciler()
    src = PlannedSession(
        session_id="sess-01",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="VO2",
        duration_minutes=60,
        target_tss=70.0,
        intensity="HIGH",
        priority=4,
        rationale=("Intervals",),
    )
    rec = make_test_decision_record("dec-01", DecisionAction.PROCEED, "SIG_ALL_GOOD")

    rx = reconciler.reconcile("plan-1", src, rec)

    assert rx.prescription_id == "sess-01:dec-01"
    assert rx.plan_id == "plan-1"
    assert rx.decision_id == "dec-01"
    assert rx.disposition == PrescriptionDisposition.AS_PLANNED
    assert rx.prescribed_kind == PlannedSessionKind.TRAINING
    assert rx.prescribed_session_type == "VO2"
    assert rx.prescribed_duration_minutes == 60
    assert rx.prescribed_target_tss == 70.0
    assert rx.prescribed_intensity == "HIGH"
    assert rx.reason_codes == ("SIG_ALL_GOOD",)
    assert rx.generated_at == rec.recorded_at
    assert rx.reconciliation_policy_version == "1.0"


def test_reconcile_training_reduce():
    reconciler = DailyTrainingReconciler()
    src = PlannedSession(
        session_id="sess-02",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="THRESHOLD",
        duration_minutes=90,
        target_tss=100.0,
        intensity="HIGH",
        priority=4,
        rationale=("FTP build",),
    )
    rec = make_test_decision_record("dec-02", DecisionAction.REDUCE, "SIG_FATIGUE_WARN")

    rx = reconciler.reconcile("plan-1", src, rec)

    assert rx.disposition == PrescriptionDisposition.REDUCED
    assert rx.prescribed_kind == PlannedSessionKind.TRAINING
    assert rx.prescribed_session_type == "THRESHOLD"
    assert rx.prescribed_duration_minutes == 62  # int(90 * 0.70) = int(62.99999...) = 62
    assert rx.prescribed_target_tss == pytest.approx(70.0)  # 100.0 * 0.70
    assert rx.prescribed_intensity == "HIGH"


def test_reconcile_training_reduce_truncation_and_none_tss():
    reconciler = DailyTrainingReconciler()
    src = PlannedSession(
        session_id="sess-02b",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="ENDURANCE",
        duration_minutes=45,
        target_tss=None,
        intensity="MODERATE",
        priority=3,
        rationale=("Base",),
    )
    rec = make_test_decision_record("dec-02b", DecisionAction.REDUCE, "SIG_LOAD_WARN")

    rx = reconciler.reconcile("plan-1", src, rec)

    assert rx.disposition == PrescriptionDisposition.REDUCED
    assert rx.prescribed_duration_minutes == 31  # int(45 * 0.70)
    assert rx.prescribed_target_tss is None


def test_reconcile_training_replace_with_recovery():
    reconciler = DailyTrainingReconciler()

    # Case 1: original duration > 45 -> capped at 45
    src_long = PlannedSession(
        session_id="sess-03a",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="VO2",
        duration_minutes=90,
        target_tss=80.0,
        intensity="HIGH",
        priority=4,
        rationale=("Hard VO2",),
    )
    rec = make_test_decision_record("dec-03a", DecisionAction.REPLACE_WITH_RECOVERY, "SIG_LOW_HRV")

    rx_long = reconciler.reconcile("plan-1", src_long, rec)
    assert rx_long.disposition == PrescriptionDisposition.RECOVERY_REPLACEMENT
    assert rx_long.prescribed_kind == PlannedSessionKind.TRAINING
    assert rx_long.prescribed_session_type == "RECOVERY"
    assert rx_long.prescribed_duration_minutes == 45
    assert rx_long.prescribed_target_tss is None
    assert rx_long.prescribed_intensity == "LOW"

    # Case 2: original duration < 45 -> preserved original duration (e.g. 30)
    src_short = PlannedSession(
        session_id="sess-03b",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="SPINT",
        duration_minutes=30,
        target_tss=40.0,
        intensity="HIGH",
        priority=4,
        rationale=("Short Sprints",),
    )
    rx_short = reconciler.reconcile("plan-1", src_short, rec)
    assert rx_short.prescribed_duration_minutes == 30


def test_reconcile_training_rest_and_review():
    reconciler = DailyTrainingReconciler()
    src = PlannedSession(
        session_id="sess-04",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="VO2",
        duration_minutes=60,
        target_tss=70.0,
        intensity="HIGH",
        priority=4,
        rationale=("VO2",),
    )

    rec_rest = make_test_decision_record("dec-rest", DecisionAction.REST, "SIG_KRYTYCZNA_REGENERACJA")
    rx_rest = reconciler.reconcile("plan-1", src, rec_rest)
    assert rx_rest.disposition == PrescriptionDisposition.REST
    assert rx_rest.prescribed_kind == PlannedSessionKind.REST
    assert rx_rest.prescribed_duration_minutes == 0
    assert rx_rest.prescribed_target_tss == 0.0

    rec_review = make_test_decision_record("dec-rev", DecisionAction.REVIEW, "SIG_LAB_CRITICAL")
    rx_rev = reconciler.reconcile("plan-1", src, rec_review)
    assert rx_rev.disposition == PrescriptionDisposition.HOLD_FOR_REVIEW
    assert rx_rev.prescribed_kind is None
    assert rx_rev.prescribed_duration_minutes is None
    assert rx_rev.prescribed_target_tss is None


def test_reconcile_explicit_rest_non_escalation_rule():
    reconciler = DailyTrainingReconciler()
    rest_src = PlannedSession(
        session_id="sess-rest-planned",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.REST,
        session_type=None,
        duration_minutes=0,
        target_tss=None,
        intensity=None,
        priority=1,
        rationale=("Scheduled Rest",),
    )

    # 1. PROCEED + planned REST -> AS_PLANNED / REST
    rx_proceed = reconciler.reconcile("p1", rest_src, make_test_decision_record("d1", DecisionAction.PROCEED))
    assert rx_proceed.disposition == PrescriptionDisposition.AS_PLANNED
    assert rx_proceed.prescribed_kind == PlannedSessionKind.REST

    # 2. REDUCE + planned REST -> REST
    rx_reduce = reconciler.reconcile("p1", rest_src, make_test_decision_record("d2", DecisionAction.REDUCE))
    assert rx_reduce.disposition == PrescriptionDisposition.REST
    assert rx_reduce.prescribed_kind == PlannedSessionKind.REST

    # 3. REPLACE_WITH_RECOVERY + planned REST -> REST (Never escalated to recovery workout)
    rx_rec = reconciler.reconcile("p1", rest_src, make_test_decision_record("d3", DecisionAction.REPLACE_WITH_RECOVERY))
    assert rx_rec.disposition == PrescriptionDisposition.REST
    assert rx_rec.prescribed_kind == PlannedSessionKind.REST

    # 4. REST + planned REST -> REST
    rx_rest = reconciler.reconcile("p1", rest_src, make_test_decision_record("d4", DecisionAction.REST))
    assert rx_rest.disposition == PrescriptionDisposition.REST
    assert rx_rest.prescribed_kind == PlannedSessionKind.REST

    # 5. REVIEW + planned REST -> HOLD_FOR_REVIEW
    rx_rev = reconciler.reconcile("p1", rest_src, make_test_decision_record("d5", DecisionAction.REVIEW))
    assert rx_rev.disposition == PrescriptionDisposition.HOLD_FOR_REVIEW
    assert rx_rev.prescribed_kind is None


def test_reconciliation_determinism_and_immutability():
    reconciler = DailyTrainingReconciler()
    src = PlannedSession(
        session_id="sess-det",
        date=date(2026, 8, 10),
        kind=PlannedSessionKind.TRAINING,
        session_type="TEMPO",
        duration_minutes=60,
        target_tss=50.0,
        intensity="MODERATE",
        priority=3,
        rationale=("Tempo",),
    )
    rec = make_test_decision_record("dec-det", DecisionAction.REDUCE, "SIG_FATIGUE")

    rx1 = reconciler.reconcile("plan-det", src, rec)
    rx2 = reconciler.reconcile("plan-det", src, rec)

    assert rx1 == rx2
    # Verify source PlannedSession and DecisionAuditRecord are unchanged
    assert src.duration_minutes == 60
    assert src.kind == PlannedSessionKind.TRAINING
    assert rec.policy_result.action == DecisionAction.REDUCE
