"""Unit and integration tests for Stage 26.5 production adaptive daily runtime integration."""
from datetime import date, datetime, timezone
from unittest.mock import MagicMock
import pytest

from application.adaptive_daily_coordinator import (
    AdaptiveDailyRuntimeCoordinator,
    AdaptiveDailyRuntimeOutcome,
)
from application.adaptive_daily_production_composition import (
    create_production_adaptive_daily_runtime,
)
from application.training_plan_decision_context import (
    MissingTrainingPlanError,
    TrainingPlanDecisionContextAdapter,
)
from decision.daily_coordinator import CoordinatorExecutionResult, DailyDecisionRuntimeCoordinator
from decision.daily_execution import DailyCoordinatorOutcome, calculate_local_run_date
from decision.daily_repository import DailyExecutionRepository
from decision.persistence import DuckDbDailyExecutionRepository
from decision.history_v2 import DecisionAuditRecord
from decision.persistence import DuckDbDecisionAuditRecordRepository
from decision.policy_v2 import DecisionAction, DecisionSeverity
from decision.runtime_workflow import DecisionClock
from morning_briefing.input_models import (
    MorningBriefingInput,
    TrainingBriefingInput,
)
from morning_briefing.provider import MorningBriefingInputProvider
from scripts.run_daily_decision_runtime import run_daily_decision_runtime
from training_plan.builder import BaselineTrainingPlanBuilder
from training_plan.intent import TrainingIntent, Weekday, WeeklySessionIntent
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.persistence.duckdb_repository import (
    DuckDbFinalSessionPrescriptionRepository,
    DuckDbTrainingPlanRepository,
)
from training_plan.prescription import PrescriptionDisposition
from training_plan.provider import RepositoryTrainingPlanProvider


class FixedTestClock(DecisionClock):
    def __init__(self, fixed_dt: datetime) -> None:
        self._dt = fixed_dt
    def now(self) -> datetime:
        return self._dt


def build_7day_intent() -> TrainingIntent:
    return TrainingIntent(
        intent_id="intent-7day-test",
        weekly_sessions=(
            WeeklySessionIntent(Weekday.MONDAY, PlannedSessionKind.TRAINING, "VO2", 60, 80.0, "HIGH", 4, ("Intervals",)),
            WeeklySessionIntent(Weekday.TUESDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
            WeeklySessionIntent(Weekday.WEDNESDAY, PlannedSessionKind.TRAINING, "THRESHOLD", 90, 100.0, "HIGH", 4, ("FTP",)),
            WeeklySessionIntent(Weekday.THURSDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
            WeeklySessionIntent(Weekday.FRIDAY, PlannedSessionKind.TRAINING, "ENDURANCE", 120, 90.0, "MODERATE", 3, ("Base",)),
            WeeklySessionIntent(Weekday.SATURDAY, PlannedSessionKind.TRAINING, "TEMPO", 90, 85.0, "MODERATE", 3, ("Tempo",)),
            WeeklySessionIntent(Weekday.SUNDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
        ),
    )


class MockMorningBriefingProvider(MorningBriefingInputProvider):
    def get_input(self) -> MorningBriefingInput:
        return MorningBriefingInput(
            generated_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
            recovery=None,
            training=TrainingBriefingInput(
                title="VO2 Intervals",
                description="High intensity VO2 session",
                duration_minutes=60,
                intensity="HIGH",
                is_available=True,
                session_type="VO2",
                recent_training_load=45.0,
                fatigue_status="MODERATE",
            ),
            biomarkers=None,
        )


def test_training_plan_decision_context_adapter_training_and_rest(tmp_path):
    tp_file = tmp_path / "tp.duckdb"
    tp_repo = DuckDbTrainingPlanRepository(db_path=tp_file)

    builder = BaselineTrainingPlanBuilder()
    plan = builder.build(
        intent=build_7day_intent(),
        start_date=date(2026, 8, 10), # Monday
        end_date=date(2026, 8, 16), # Sunday
        plan_id="plan-adapter-01",
        generated_at=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc),
    )
    tp_repo.save(plan)
    provider = RepositoryTrainingPlanProvider(repository=tp_repo)
    mb_provider = MockMorningBriefingProvider()

    adapter = TrainingPlanDecisionContextAdapter(
        training_plan_provider=provider,
        briefing_provider=mb_provider,
        default_timezone_name="Europe/Warsaw",
    )

    # 1. Monday 2026-08-10 -> TRAINING session
    ctx_mon = adapter.get_context(generated_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc))
    assert ctx_mon.status.value == "available"
    assert ctx_mon.planned_session_type == "VO2"
    assert ctx_mon.planned_duration_minutes == 60
    assert ctx_mon.planned_intensity == "HIGH"
    assert ctx_mon.plan_id == "plan-adapter-01"
    assert ctx_mon.planned_session_id == "plan-adapter-01:2026-08-10"
    assert ctx_mon.recent_training_load == 45.0
    assert ctx_mon.fatigue_status == "MODERATE"

    # 2. Tuesday 2026-08-11 -> Explicit REST session
    ctx_tue = adapter.get_context(generated_at=datetime(2026, 8, 11, 7, 0, tzinfo=timezone.utc))
    assert ctx_tue.status.value == "available"
    assert ctx_tue.planned_session_type == "REST"
    assert ctx_tue.planned_duration_minutes == 0
    assert ctx_tue.planned_intensity is None
    assert ctx_tue.plan_id == "plan-adapter-01"
    assert ctx_tue.planned_session_id == "plan-adapter-01:2026-08-11"

    # 3. Missing plan date -> raises MissingTrainingPlanError
    with pytest.raises(MissingTrainingPlanError):
        adapter.get_context(generated_at=datetime(2026, 8, 20, 7, 0, tzinfo=timezone.utc))


def test_adaptive_daily_runtime_normal_execution_and_idempotency(tmp_path):
    tp_file = tmp_path / "tp.duckdb"
    dec_file = tmp_path / "dec.duckdb"

    tp_repo = DuckDbTrainingPlanRepository(db_path=tp_file)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=tp_file)

    builder = BaselineTrainingPlanBuilder()
    plan = builder.build(
        intent=build_7day_intent(),
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-run-01",
        generated_at=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc),
    )
    tp_repo.save(plan)

    clock = FixedTestClock(datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc))

    with create_production_adaptive_daily_runtime(
        decisions_db_path=dec_file,
        training_plan_db_path=tp_file,
        clock=clock,
    ) as container:
        # First execution -> EXECUTED
        res1 = container.coordinator.run_adaptive_daily()
        assert res1.outcome == AdaptiveDailyRuntimeOutcome.EXECUTED
        assert res1.run_date_str == "2026-08-10"
        assert res1.decision_id is not None
        assert res1.prescription_id == f"plan-run-01:2026-08-10:{res1.decision_id}"

        # Assert DB state
        audit_rec = container.audit_repository.get_by_id(res1.decision_id)
        assert audit_rec is not None
        assert audit_rec.context.training.plan_id == "plan-run-01"
        assert audit_rec.context.training.planned_session_id == "plan-run-01:2026-08-10"

        rx = rx_repo.get_by_id(res1.prescription_id)
        assert rx is not None
        assert rx.plan_id == "plan-run-01"
        assert rx.decision_id == res1.decision_id

        # Second execution same day -> SKIPPED_ALREADY_COMPLETED
        res2 = container.coordinator.run_adaptive_daily()
        assert res2.outcome == AdaptiveDailyRuntimeOutcome.SKIPPED_ALREADY_COMPLETED
        assert res2.decision_id == res1.decision_id
        assert res2.prescription_id == res1.prescription_id

        # Verify exactly 1 audit record and 1 prescription exist
        assert len(container.audit_repository.list_records()) == 1
        assert len(rx_repo.list_records()) == 1


def test_adaptive_daily_runtime_crash_recovery(tmp_path):
    tp_file = tmp_path / "tp.duckdb"
    dec_file = tmp_path / "dec.duckdb"

    tp_repo = DuckDbTrainingPlanRepository(db_path=tp_file)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=tp_file)

    builder = BaselineTrainingPlanBuilder()
    plan = builder.build(
        intent=build_7day_intent(),
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-crash-01",
        generated_at=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc),
    )
    tp_repo.save(plan)

    clock = FixedTestClock(datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc))

    # Run initial execution
    with create_production_adaptive_daily_runtime(
        decisions_db_path=dec_file,
        training_plan_db_path=tp_file,
        clock=clock,
    ) as container:
        res1 = container.coordinator.run_adaptive_daily()
        assert res1.outcome == AdaptiveDailyRuntimeOutcome.EXECUTED

    # Delete prescription to simulate crash window (Decision saved + Ledger completed, but prescription missing)
    conn = rx_repo._get_connection()
    conn.execute("DELETE FROM final_session_prescriptions")
    conn.close()
    assert rx_repo.get_latest() is None

    # Next execution -> RECOVERED_COMPLETED (missing prescription created without recalculating decision)
    with create_production_adaptive_daily_runtime(
        decisions_db_path=dec_file,
        training_plan_db_path=tp_file,
        clock=clock,
    ) as container:
        res2 = container.coordinator.run_adaptive_daily()
        assert res2.outcome == AdaptiveDailyRuntimeOutcome.RECOVERED_COMPLETED
        assert res2.decision_id == res1.decision_id
        assert rx_repo.get_latest() is not None


def test_adaptive_daily_runtime_missing_plan_outcome(tmp_path):
    tp_file = tmp_path / "tp_empty.duckdb"
    dec_file = tmp_path / "dec_empty.duckdb"

    clock = FixedTestClock(datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc))

    with create_production_adaptive_daily_runtime(
        decisions_db_path=dec_file,
        training_plan_db_path=tp_file,
        clock=clock,
    ) as container:
        res = container.coordinator.run_adaptive_daily()
        assert res.outcome == AdaptiveDailyRuntimeOutcome.MISSING_PLAN
        assert len(container.audit_repository.list_records()) == 0
        assert container.daily_repository.get_by_run_date(date(2026, 8, 10)) is None
        assert container.prescription_repository.get_latest() is None


def test_cli_missing_plan_exit_code_1(tmp_path):
    tp_file = tmp_path / "tp_cli.duckdb"
    dec_file = tmp_path / "dec_cli.duckdb"

    code = run_daily_decision_runtime(
        decisions_db_path=dec_file,
        training_plan_db_path=tp_file,
    )
    assert code == 1


def test_adaptive_daily_runtime_plan_version_race(tmp_path):
    """Verifies that if Plan B is saved after Decision was generated from Plan A, recovery uses Plan A."""
    tp_file = tmp_path / "tp_race.duckdb"
    dec_file = tmp_path / "dec_race.duckdb"

    tp_repo = DuckDbTrainingPlanRepository(db_path=tp_file)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=tp_file)
    builder = BaselineTrainingPlanBuilder()

    # 1. Build & save Plan A (covering 2026-08-10)
    intent_a = build_7day_intent()
    plan_a = builder.build(
        intent=intent_a,
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-version-A",
        generated_at=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc),
    )
    tp_repo.save(plan_a)

    clock = FixedTestClock(datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc))

    # 2. Run decision generation with Plan A present
    with create_production_adaptive_daily_runtime(
        decisions_db_path=dec_file,
        training_plan_db_path=tp_file,
        clock=clock,
    ) as container:
        res1 = container.coordinator.run_adaptive_daily()
        assert res1.outcome == AdaptiveDailyRuntimeOutcome.EXECUTED
        decision_id = res1.decision_id

    # 3. Simulate crash window before prescription save by deleting prescription
    conn = rx_repo._get_connection()
    conn.execute("DELETE FROM final_session_prescriptions")
    conn.close()

    # 4. Save Plan B (superseding/newer plan covering same target date 2026-08-10 with different intent)
    intent_b = TrainingIntent(
        intent_id="intent-version-B",
        weekly_sessions=(
            WeeklySessionIntent(Weekday.MONDAY, PlannedSessionKind.TRAINING, "ENDURANCE", 180, 150.0, "MODERATE", 3, ("Long Ride",)),
            WeeklySessionIntent(Weekday.TUESDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
            WeeklySessionIntent(Weekday.WEDNESDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
            WeeklySessionIntent(Weekday.THURSDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
            WeeklySessionIntent(Weekday.FRIDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
            WeeklySessionIntent(Weekday.SATURDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
            WeeklySessionIntent(Weekday.SUNDAY, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",)),
        ),
    )
    plan_b = builder.build(
        intent=intent_b,
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-version-B",
        generated_at=datetime(2026, 8, 8, 10, 0, tzinfo=timezone.utc),
    )
    tp_repo.save(plan_b)

    # 5. Execute adaptive recovery
    with create_production_adaptive_daily_runtime(
        decisions_db_path=dec_file,
        training_plan_db_path=tp_file,
        clock=clock,
    ) as container:
        res2 = container.coordinator.run_adaptive_daily()
        assert res2.outcome == AdaptiveDailyRuntimeOutcome.RECOVERED_COMPLETED
        assert res2.decision_id == decision_id

        # Verify prescription was generated from Plan A (VO2, 60m), ignoring Plan B (ENDURANCE, 180m)
        rx = rx_repo.get_by_id(res2.prescription_id)
        assert rx is not None
        assert rx.plan_id == "plan-version-A"
        assert rx.source_session.session_type == "VO2"
        assert rx.source_session.duration_minutes == 60


def test_adaptive_daily_runtime_review_end_to_end(tmp_path):
    """Verifies end-to-end reconciliation for a REVIEW decision action."""
    tp_file = tmp_path / "tp_review.duckdb"
    dec_file = tmp_path / "dec_review.duckdb"

    tp_repo = DuckDbTrainingPlanRepository(db_path=tp_file)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=tp_file)
    builder = BaselineTrainingPlanBuilder()

    plan = builder.build(
        intent=build_7day_intent(),
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-review-01",
        generated_at=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc),
    )
    tp_repo.save(plan)

    from decision.context import (
        ContextDataStatus,
        TrainingDecisionContext,
        RecoveryDecisionContext,
        BiomarkerDecisionContext,
        PerformanceDecisionContext,
        AthleteDecisionContext,
    )
    from decision.history_v2 import DecisionAuditRecord
    from decision.policy_v2 import DecisionAction, DecisionPolicyResult, DecisionSeverity
    from application.training_plan_reconciliation import DailyTrainingReconciler

    planned_session = plan.sessions[0] # Monday VO2 60m
    from decision.policy_v2 import DecisionAction, DecisionPolicyResult, DecisionPolicySignal, DecisionSeverity
    from decision.recommendation_plan import RecommendationPlanBuilder
    rec_builder = RecommendationPlanBuilder()

    policy_res = DecisionPolicyResult(
        generated_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
        action=DecisionAction.REVIEW,
        severity=DecisionSeverity.CRITICAL,
        signals=(DecisionPolicySignal("SIG_01", "biomarkers", DecisionSeverity.CRITICAL, "Critical biomarker"),),
        confidence=0.95,
        policy_version="2.0",
    )

    dec_record = DecisionAuditRecord(
        decision_id="dec-review-100",
        recorded_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
        context=AthleteDecisionContext(
            generated_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
            recovery=RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE),
            training=TrainingDecisionContext(
                status=ContextDataStatus.AVAILABLE,
                planned_session_type="VO2",
                planned_duration_minutes=60,
                planned_intensity="HIGH",
                plan_id="plan-review-01",
                planned_session_id=planned_session.session_id,
            ),
            biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.UNAVAILABLE, attention_count=0, critical_count=0),
            performance=PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE),
        ),
        policy_result=policy_res,
        recommendation_plan=rec_builder.build(policy_res),
    )

    reconciler = DailyTrainingReconciler()
    prescription = reconciler.reconcile(
        plan_id="plan-review-01",
        planned_session=planned_session,
        decision_record=dec_record,
    )

    assert prescription.disposition == PrescriptionDisposition.HOLD_FOR_REVIEW
    assert prescription.prescribed_kind is None
    assert prescription.prescribed_session_type is None
    assert prescription.prescribed_duration_minutes is None
    assert prescription.prescribed_target_tss is None
    assert prescription.prescribed_intensity is None


def test_adaptive_daily_runtime_legacy_decision_recovery(tmp_path):
    """Verifies that legacy decision record without plan_id results in controlled FAILED outcome."""
    tp_file = tmp_path / "tp_legacy.duckdb"
    dec_file = tmp_path / "dec_legacy.duckdb"

    tp_repo = DuckDbTrainingPlanRepository(db_path=tp_file)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=tp_file)
    audit_repo = DuckDbDecisionAuditRecordRepository(db_path=dec_file)
    builder = BaselineTrainingPlanBuilder()

    plan = builder.build(
        intent=build_7day_intent(),
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 16),
        plan_id="plan-legacy-01",
        generated_at=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc),
    )
    tp_repo.save(plan)

    # Save legacy DecisionAuditRecord (without plan_id or planned_session_id)
    from decision.context import (
        ContextDataStatus,
        TrainingDecisionContext,
        RecoveryDecisionContext,
        BiomarkerDecisionContext,
        PerformanceDecisionContext,
        AthleteDecisionContext,
    )
    from decision.policy_v2 import DecisionAction, DecisionPolicyResult, DecisionPolicySignal, DecisionSeverity
    from decision.recommendation_plan import RecommendationPlanBuilder

    legacy_policy = DecisionPolicyResult(
        generated_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
        action=DecisionAction.PROCEED,
        severity=DecisionSeverity.LOW,
        signals=(DecisionPolicySignal("SIG_NORMAL", "recovery", DecisionSeverity.LOW, "Normal status"),),
        confidence=0.60,
        policy_version="2.0",
    )

    rec_builder = RecommendationPlanBuilder()
    legacy_rec = DecisionAuditRecord(
        decision_id="dec-legacy-999",
        recorded_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
        context=AthleteDecisionContext(
            generated_at=datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc),
            recovery=RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE),
            training=TrainingDecisionContext(
                status=ContextDataStatus.AVAILABLE,
                planned_session_type="VO2",
                planned_duration_minutes=60,
                planned_intensity="HIGH",
                plan_id=None,
                planned_session_id=None,
            ),
            biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.UNAVAILABLE, attention_count=0, critical_count=0),
            performance=PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE),
        ),
        policy_result=legacy_policy,
        recommendation_plan=rec_builder.build(legacy_policy),
    )
    audit_repo.save(legacy_rec)

    # Test legacy decoding
    decoded = audit_repo.get_by_id("dec-legacy-999")
    assert decoded is not None
    assert decoded.context.training.plan_id is None
    assert decoded.context.training.planned_session_id is None

    # Test adaptive coordinator refusal of legacy record
    mock_coord = MagicMock()
    mock_coord._clock.now.return_value = datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc)
    mock_coord._timezone_name = "Europe/Warsaw"
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.SKIPPED_ALREADY_COMPLETED,
        run_date_str="2026-08-10",
        decision_id="dec-legacy-999",
    )

    adaptive_coord = AdaptiveDailyRuntimeCoordinator(
        decision_coordinator=mock_coord,
        decision_audit_repository=audit_repo,
        training_plan_repository=tp_repo,
        prescription_repository=rx_repo,
    )

    res = adaptive_coord.run_adaptive_daily()
    assert res.outcome == AdaptiveDailyRuntimeOutcome.FAILED
