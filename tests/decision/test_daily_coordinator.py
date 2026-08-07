from datetime import date, datetime, timedelta, timezone
import duckdb
import pytest

from decision import (
    AthleteDecisionContextBuilder,
    BiomarkerDecisionContext,
    ContextDataStatus,
    CoordinatorExecutionResult,
    DailyCoordinatorOutcome,
    DailyDecisionRuntimeCoordinator,
    DailyExecutionLedgerState,
    DecisionAuditRecordBuilder,
    DecisionClock,
    DecisionPolicyV2,
    DuckDbDailyExecutionRepository,
    DuckDbDecisionAuditRecordRepository,
    FixedDecisionIdGenerator,
    PerformanceDecisionContext,
    RecommendationPlanBuilder,
    RecoveryDecisionContext,
    TrainingDecisionContext,
    create_persisted_decision_runtime_application,
)
from morning_briefing.provider import EmptyMorningBriefingInputProvider
from performance_lab.provider import EmptyPerformanceTestHistoryProvider


class MutableTestClock:
    def __init__(self, current_time: datetime):
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


@pytest.fixture
def test_setup(tmp_path):
    dec_db = tmp_path / "decisions.duckdb"
    conn = duckdb.connect(str(dec_db))
    audit_repo = DuckDbDecisionAuditRecordRepository(conn=conn)
    daily_repo = DuckDbDailyExecutionRepository(conn=conn)

    def container_factory(fixed_gen: FixedDecisionIdGenerator):
        app = create_persisted_decision_runtime_application(
            morning_briefing_provider=EmptyMorningBriefingInputProvider(),
            performance_history_provider=EmptyPerformanceTestHistoryProvider(),
            repository=audit_repo,
            id_generator=fixed_gen,
        )
        return DummyContainer(app)

    class DummyContainer:
        def __init__(self, app):
            self.app = app
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    return daily_repo, audit_repo, container_factory, dec_db, str(dec_db)


def test_coordinator_first_run_executes_successfully(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    res = coordinator.run_daily_if_needed()
    assert res.outcome == DailyCoordinatorOutcome.EXECUTED
    assert res.run_date_str == "2026-08-07"
    assert res.decision_id is not None

    # Check ledger state
    ledger_entry = daily_repo.get_by_run_date(date(2026, 8, 7))
    assert ledger_entry is not None
    assert ledger_entry.status == DailyExecutionLedgerState.COMPLETED
    assert ledger_entry.decision_id == res.decision_id

    # Check audit record state
    audit_rec = audit_repo.get_by_id(res.decision_id)
    assert audit_rec is not None
    assert audit_rec.decision_id == res.decision_id


def test_coordinator_second_run_same_day_skips(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    res1 = coordinator.run_daily_if_needed()
    assert res1.outcome == DailyCoordinatorOutcome.EXECUTED

    # Second run on same day
    res2 = coordinator.run_daily_if_needed()
    assert res2.outcome == DailyCoordinatorOutcome.SKIPPED_ALREADY_COMPLETED
    assert res2.decision_id == res1.decision_id

    # Audit records count remains 1
    records = audit_repo.list_records()
    assert len(records) == 1


def test_coordinator_next_day_executes_new_decision(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    res1 = coordinator.run_daily_if_needed()
    assert res1.outcome == DailyCoordinatorOutcome.EXECUTED

    # Advance clock to next day
    clock.current_time = datetime(2026, 8, 8, 8, 0, 0, tzinfo=timezone.utc)
    res2 = coordinator.run_daily_if_needed()
    assert res2.outcome == DailyCoordinatorOutcome.EXECUTED
    assert res2.run_date_str == "2026-08-08"
    assert res2.decision_id != res1.decision_id

    records = audit_repo.list_records()
    assert len(records) == 2


def test_coordinator_timezone_boundary_execution(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    # 23:30 UTC on Aug 7 -> 01:30 CEST on Aug 8 (Europe/Warsaw)
    t0 = datetime(2026, 8, 7, 23, 30, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    res = coordinator.run_daily_if_needed()
    assert res.outcome == DailyCoordinatorOutcome.EXECUTED
    assert res.run_date_str == "2026-08-08"


def test_coordinator_manual_cli_run_isolation(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    # Seed a manual decision in audit repo for today WITHOUT ledger entry
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=80.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    ctx = AthleteDecisionContextBuilder().build(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)
    pol_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(pol_res)
    manual_record = DecisionAuditRecordBuilder().build("manual-dec-1", now, ctx, pol_res, plan)

    audit_repo.save(manual_record)
    assert len(audit_repo.list_records()) == 1

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    # Automated coordinator should execute normally despite existing manual audit record
    res = coordinator.run_daily_if_needed()
    assert res.outcome == DailyCoordinatorOutcome.EXECUTED
    assert res.decision_id != "manual-dec-1"
    assert len(audit_repo.list_records()) == 2


def test_coordinator_crash_recovery_after_persistence(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    # Simulate crash state: ledger is RUNNING with decision_id X, but audit record X WAS persisted before process died
    now = t0
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=80.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    ctx = AthleteDecisionContextBuilder().build(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)
    pol_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(pol_res)
    persisted_record = DecisionAuditRecordBuilder().build("decision-crash-1", now, ctx, pol_res, plan)
    audit_repo.save(persisted_record)

    # Ledger reserved decision-crash-1 but remains in RUNNING
    from decision.daily_execution import DailyExecutionRecord
    daily_repo.reserve(
        DailyExecutionRecord(
            run_date=date(2026, 8, 7),
            status=DailyExecutionLedgerState.RUNNING,
            decision_id="decision-crash-1",
            timezone_name="Europe/Warsaw",
            started_at=t0,
            lease_expires_at=t0 + timedelta(minutes=15),
        )
    )

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    res = coordinator.run_daily_if_needed()
    assert res.outcome == DailyCoordinatorOutcome.RECOVERED_COMPLETED
    assert res.decision_id == "decision-crash-1"

    # Ledger state is updated to COMPLETED
    ledger_entry = daily_repo.get_by_run_date(date(2026, 8, 7))
    assert ledger_entry.status == DailyExecutionLedgerState.COMPLETED
    assert len(audit_repo.list_records()) == 1


def test_coordinator_active_lease_skips_in_progress(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    # Active RUNNING lease with no audit record yet
    from decision.daily_execution import DailyExecutionRecord
    daily_repo.reserve(
        DailyExecutionRecord(
            run_date=date(2026, 8, 7),
            status=DailyExecutionLedgerState.RUNNING,
            decision_id="decision-active-1",
            timezone_name="Europe/Warsaw",
            started_at=t0,
            lease_expires_at=t0 + timedelta(minutes=15),
        )
    )

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    # Current time is t0 + 5 min (lease active until t0 + 15 min)
    clock.current_time = t0 + timedelta(minutes=5)
    res = coordinator.run_daily_if_needed()
    assert res.outcome == DailyCoordinatorOutcome.SKIPPED_IN_PROGRESS
    assert res.decision_id == "decision-active-1"


def test_coordinator_expired_lease_takes_over_and_executes(test_setup):
    daily_repo, audit_repo, container_factory, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    # Expired RUNNING lease
    from decision.daily_execution import DailyExecutionRecord
    daily_repo.reserve(
        DailyExecutionRecord(
            run_date=date(2026, 8, 7),
            status=DailyExecutionLedgerState.RUNNING,
            decision_id="decision-expired-1",
            timezone_name="Europe/Warsaw",
            started_at=t0,
            lease_expires_at=t0 + timedelta(minutes=15),
        )
    )

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    # Current time is t0 + 30 min (lease expired)
    clock.current_time = t0 + timedelta(minutes=30)
    res = coordinator.run_daily_if_needed()
    assert res.outcome == DailyCoordinatorOutcome.EXECUTED
    assert res.decision_id == "decision-expired-1"  # Reuses same pre-reserved ID

    ledger_entry = daily_repo.get_by_run_date(date(2026, 8, 7))
    assert ledger_entry.status == DailyExecutionLedgerState.COMPLETED
    assert ledger_entry.attempt_count == 2


def test_coordinator_failed_run_retry(test_setup):
    daily_repo, audit_repo, _, _, _ = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)
    clock = MutableTestClock(t0)

    failing = True

    def failing_container_factory(fixed_gen: FixedDecisionIdGenerator):
        nonlocal failing
        if failing:
            raise RuntimeError("Database connection lost")
        app = create_persisted_decision_runtime_application(
            morning_briefing_provider=EmptyMorningBriefingInputProvider(),
            performance_history_provider=EmptyPerformanceTestHistoryProvider(),
            repository=audit_repo,
            id_generator=fixed_gen,
        )
        class DummyContainer:
            def __init__(self, app): self.app = app
            def __enter__(self): return self
            def __exit__(self, *args): pass
        return DummyContainer(app)

    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=failing_container_factory,
        clock=clock,
        timezone_name="Europe/Warsaw",
    )

    # First attempt fails
    res1 = coordinator.run_daily_if_needed()
    assert res1.outcome == DailyCoordinatorOutcome.FAILED
    assert "RuntimeError" in res1.record.error_message

    ledger1 = daily_repo.get_by_run_date(date(2026, 8, 7))
    assert ledger1.status == DailyExecutionLedgerState.FAILED

    # Fix error and retry
    failing = False
    clock.current_time = t0 + timedelta(minutes=10)
    res2 = coordinator.run_daily_if_needed()
    assert res2.outcome == DailyCoordinatorOutcome.EXECUTED
    assert res2.decision_id == res1.decision_id
    assert res2.record.attempt_count == 2
    assert res2.record.status == DailyExecutionLedgerState.COMPLETED



def test_coordinator_concurrency_reservation_race(test_setup):
    daily_repo, audit_repo, container_factory, _, db_path = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)

    import concurrent.futures
    import threading

    barrier = threading.Barrier(2)

    def run_contender(cid: str):
        thread_conn = duckdb.connect(db_path)
        th_audit_repo = DuckDbDecisionAuditRecordRepository(conn=thread_conn)
        th_daily_repo = DuckDbDailyExecutionRepository(conn=thread_conn)

        def th_container_factory(fixed_gen: FixedDecisionIdGenerator):
            app = create_persisted_decision_runtime_application(
                morning_briefing_provider=EmptyMorningBriefingInputProvider(),
                performance_history_provider=EmptyPerformanceTestHistoryProvider(),
                repository=th_audit_repo,
                id_generator=fixed_gen,
            )
            class DummyContainer:
                def __init__(self, app): self.app = app
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return DummyContainer(app)

        coord = DailyDecisionRuntimeCoordinator(
            daily_repository=th_daily_repo,
            audit_repository=th_audit_repo,
            container_factory=th_container_factory,
            clock=MutableTestClock(t0),
            id_factory=lambda: f"dec-race-{cid}",
        )
        barrier.wait()
        res = coord.run_daily_if_needed()
        thread_conn.close()
        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_contender, "1")
        f2 = executor.submit(run_contender, "2")
        r1 = f1.result()
        r2 = f2.result()

    outcomes = [r1.outcome, r2.outcome]
    # Exactly one executed, the other skipped
    exec_count = sum(1 for o in outcomes if o == DailyCoordinatorOutcome.EXECUTED)
    assert exec_count == 1

    records = audit_repo.list_records()
    assert len(records) == 1


def test_coordinator_takeover_concurrency_race(test_setup):
    daily_repo, audit_repo, container_factory, _, db_path = test_setup
    t0 = datetime(2026, 8, 7, 8, 0, 0, tzinfo=timezone.utc)

    # Seed an expired lease RUNNING record
    from decision.daily_execution import DailyExecutionRecord
    daily_repo.reserve(
        DailyExecutionRecord(
            run_date=date(2026, 8, 7),
            status=DailyExecutionLedgerState.RUNNING,
            decision_id="dec-takeover-race",
            timezone_name="Europe/Warsaw",
            started_at=t0,
            lease_expires_at=t0 + timedelta(minutes=15),
            attempt_count=1,
        )
    )

    import concurrent.futures
    import threading

    barrier = threading.Barrier(2)
    t_expired = t0 + timedelta(minutes=30)

    def run_takeover_contender(cid: str):
        thread_conn = duckdb.connect(db_path)
        th_audit_repo = DuckDbDecisionAuditRecordRepository(conn=thread_conn)
        th_daily_repo = DuckDbDailyExecutionRepository(conn=thread_conn)

        def th_container_factory(fixed_gen: FixedDecisionIdGenerator):
            app = create_persisted_decision_runtime_application(
                morning_briefing_provider=EmptyMorningBriefingInputProvider(),
                performance_history_provider=EmptyPerformanceTestHistoryProvider(),
                repository=th_audit_repo,
                id_generator=fixed_gen,
            )
            class DummyContainer:
                def __init__(self, app): self.app = app
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return DummyContainer(app)

        coord = DailyDecisionRuntimeCoordinator(
            daily_repository=th_daily_repo,
            audit_repository=th_audit_repo,
            container_factory=th_container_factory,
            clock=MutableTestClock(t_expired),
        )
        barrier.wait()
        res = coord.run_daily_if_needed()
        thread_conn.close()
        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_takeover_contender, "1")
        f2 = executor.submit(run_takeover_contender, "2")
        r1 = f1.result()
        r2 = f2.result()

    outcomes = [r1.outcome, r2.outcome]
    exec_count = sum(1 for o in outcomes if o == DailyCoordinatorOutcome.EXECUTED)
    assert exec_count == 1

    ledger_entry = daily_repo.get_by_run_date(date(2026, 8, 7))
    assert ledger_entry.status == DailyExecutionLedgerState.COMPLETED
    assert ledger_entry.attempt_count == 2
