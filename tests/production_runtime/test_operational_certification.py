from datetime import date, datetime, timedelta, timezone
import duckdb

from morning_briefing.input_models import MorningBriefingInput, TrainingBriefingInput
from production_runtime.diagnostics import (
    RuntimeOperationalHealth,
    RuntimeOperationalStatusReader,
    RuntimeResumability,
)
from production_runtime.models import RuntimePhase, RuntimeStatus
from production_runtime.persistence import DuckDbRuntimeAuditRepository
from production_runtime.production_composition import create_production_daily_runtime
from application.adaptive_daily_production_composition import create_production_adaptive_daily_runtime
from scripts.run_daily_decision_runtime import run_daily_decision_runtime
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.persistence.duckdb_repository import (
    DuckDbFinalSessionPrescriptionRepository,
    DuckDbTrainingPlanRepository,
)
from activity_reconciliation import DuckDbReconciliationResultRepository
from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from production_runtime.reconciliation import ProductionReconciliationAdapter
from schema.athlete_memory_schema import AthleteMemorySchema


TARGET = date(2026, 8, 11)
NOW = datetime(2026, 8, 11, 10, tzinfo=timezone.utc)


class RuntimeClock:
    def now_utc(self):
        return NOW
    def now(self):
        return NOW


class BriefingProvider:
    def __init__(self):
        self.calls = 0
    def get_input(self):
        self.calls += 1
        return MorningBriefingInput(
            generated_at=NOW,
            recovery=None,
            training=TrainingBriefingInput(
                "Endurance", "steady", 60, "MODERATE", True,
                "ENDURANCE", 150.0, "LOW",
            ),
            biomarkers=None,
        )


class InterruptOnce:
    def __init__(self, delegate):
        self.delegate = delegate
        self.interrupted = False
    def execute(self, context):
        if not self.interrupted:
            self.interrupted = True
            raise KeyboardInterrupt()
        return self.delegate.execute(context)


def fixture_options(tmp_path, provider):
    fit = tmp_path / "fits"
    fit.mkdir(exist_ok=True)
    return dict(
        target_local_date=TARGET,
        health_db_path=tmp_path / "health.duckdb",
        biomarkers_db_path=tmp_path / "biomarkers.duckdb",
        decisions_db_path=tmp_path / "decisions.duckdb",
        training_plan_db_path=tmp_path / "training_plan.duckdb",
        runtime_audit_db_path=tmp_path / "production_runtime.duckdb",
        activity_reconciliation_db_path=tmp_path / "activity_reconciliation.duckdb",
        fit_source_path=fit,
        briefing_input_provider=provider,
        clock=RuntimeClock(),
    )


def seed_plan(path):
    session = PlannedSession(
        "plan-cert:2026-08-11", TARGET, PlannedSessionKind.TRAINING,
        "ENDURANCE", 60, 50.0, "MODERATE", 3, ("certification",),
    )
    plan = TrainingPlan("plan-cert", TARGET, TARGET, 1, NOW, (session,))
    DuckDbTrainingPlanRepository(path).save(plan)


def seed_two_day_plan(path):
    closed = TARGET - timedelta(days=1)
    sessions = (
        PlannedSession(
            "plan-cert:closed-ride", closed, PlannedSessionKind.TRAINING,
            "ENDURANCE", 60, 50.0, "MODERATE", 3, ("closed",),
        ),
        PlannedSession(
            "plan-cert:today", TARGET, PlannedSessionKind.TRAINING,
            "ENDURANCE", 60, 50.0, "MODERATE", 3, ("today",),
        ),
    )
    DuckDbTrainingPlanRepository(path).save(TrainingPlan(
        "plan-cert-two-day", closed, TARGET, 1, NOW, sessions,
    ))


def seed_closed_activity(path):
    database = Database(path)
    AthleteMemorySchema(database).create()
    start = datetime(2026, 8, 10, 10)
    AthleteMemoryRepository(database).append(AthleteMemoryEvent(
        "closed-activity", start + timedelta(hours=1),
        AthleteMemoryEventType.ACTIVITY_RECORDED, "fit_file", "sha256:closed", 1,
        {"activity": {
            "start": start.isoformat(), "sport": "cycling", "duration": 3600,
        }},
    ))
    database.close()


def test_full_isolated_composition_persists_previous_day_reconciliation(tmp_path):
    provider = BriefingProvider()
    options = fixture_options(tmp_path, provider)
    seed_two_day_plan(options["training_plan_db_path"])
    seed_closed_activity(options["health_db_path"])
    options["runtime_id_factory"] = lambda: "runtime-reconciliation"

    with create_production_daily_runtime(**options) as container:
        assert isinstance(
            container.runtime._adapters[RuntimePhase.RECONCILIATION],
            ProductionReconciliationAdapter,
        )
        result = container.runtime.run_new_attempt(TARGET)

    repository = DuckDbReconciliationResultRepository(
        options["activity_reconciliation_db_path"]
    )
    persisted = repository.get_latest_for_date(TARGET - timedelta(days=1))
    phase = next(item for item in result.phases if item.phase is RuntimePhase.RECONCILIATION)
    assert result.status is RuntimeStatus.COMPLETED
    assert result.reconciliations_created == 1
    assert phase.status.value == "completed"
    assert phase.artifact_ids == (persisted.reconciliation_id,)
    assert phase.item_count == 1
    assert phase.changed_state is True
    assert persisted.finalized is True
    assert persisted.items[0].execution_outcome.value == "COMPLETED"


def test_full_isolated_candidate_and_second_attempt_are_idempotent(tmp_path):
    provider = BriefingProvider()
    options = fixture_options(tmp_path, provider)
    seed_plan(options["training_plan_db_path"])
    ids = iter(("runtime-cert-1", "runtime-cert-2"))
    options["runtime_id_factory"] = lambda: next(ids)
    with create_production_daily_runtime(**options) as container:
        first = container.runtime.run_new_attempt(TARGET)
        second = container.runtime.run_new_attempt(TARGET)
        assert first.status is second.status is RuntimeStatus.COMPLETED
        assert tuple(p.phase for p in first.phases) == tuple(RuntimePhase)
        assert first.decision_id == second.decision_id
        assert first.prescription_id == second.prescription_id
        assert container.assessment_snapshot_repository.get_by_runtime_id(first.runtime_id)
        assert container.assessment_snapshot_repository.get_by_runtime_id(second.runtime_id)
    assert len(DuckDbFinalSessionPrescriptionRepository(options["training_plan_db_path"]).list_records()) == 1
    reader = RuntimeOperationalStatusReader(
        DuckDbRuntimeAuditRepository(options["runtime_audit_db_path"], read_only=True),
        clock=RuntimeClock(),
    )
    status = reader.get_latest()
    assert status.status is RuntimeStatus.COMPLETED
    assert status.health is RuntimeOperationalHealth.HEALTHY
    assert status.resumability is RuntimeResumability.NO_ACTION


def test_restart_after_durable_assessment_uses_persisted_input(tmp_path):
    first_provider = BriefingProvider()
    options = fixture_options(tmp_path, first_provider)
    seed_plan(options["training_plan_db_path"])
    options["runtime_id_factory"] = lambda: "runtime-crash"
    with create_production_daily_runtime(**options) as container:
        original = container.runtime._adapters[RuntimePhase.DECISION]
        container.runtime._adapters[RuntimePhase.DECISION] = InterruptOnce(original)
        try:
            container.runtime.run_new_attempt(TARGET)
        except KeyboardInterrupt:
            pass
        current = DuckDbRuntimeAuditRepository(options["runtime_audit_db_path"]).get_by_runtime_id("runtime-crash")
        assert current.phases[-1].phase is RuntimePhase.ASSESSMENT
    restarted_provider = BriefingProvider()
    options["briefing_input_provider"] = restarted_provider
    with create_production_daily_runtime(**options) as container:
        completed = container.runtime.resume_attempt("runtime-crash")
        assert completed.status is RuntimeStatus.COMPLETED
    assert restarted_provider.calls == 0


def test_missing_plan_certification_is_partial_without_decision(tmp_path):
    provider = BriefingProvider()
    options = fixture_options(tmp_path, provider)
    options["runtime_id_factory"] = lambda: "runtime-no-plan"
    with create_production_daily_runtime(**options) as container:
        result = container.runtime.run_new_attempt(TARGET)
        assert result.status is RuntimeStatus.PARTIAL
        assert result.failure.code == "missing_training_plan"
        assert result.decision_id is None


def test_missing_snapshot_after_durable_assessment_is_integrity_failure(tmp_path):
    provider = BriefingProvider()
    options = fixture_options(tmp_path, provider)
    seed_plan(options["training_plan_db_path"])
    options["runtime_id_factory"] = lambda: "runtime-missing-snapshot"
    with create_production_daily_runtime(**options) as container:
        original = container.runtime._adapters[RuntimePhase.DECISION]
        container.runtime._adapters[RuntimePhase.DECISION] = InterruptOnce(original)
        try:
            container.runtime.run_new_attempt(TARGET)
        except KeyboardInterrupt:
            pass
    connection = duckdb.connect(str(options["runtime_audit_db_path"]))
    connection.execute(
        "DELETE FROM production_runtime_assessment_snapshots WHERE runtime_id = ?",
        ["runtime-missing-snapshot"],
    )
    connection.close()
    with create_production_daily_runtime(**options) as container:
        result = container.runtime.resume_attempt("runtime-missing-snapshot")
    assert result.status is RuntimeStatus.PARTIAL
    assert result.failure.code == "assessment_snapshot_missing"


def test_legacy_and_candidate_have_equivalent_decision_and_prescription_semantics(tmp_path):
    legacy_root = tmp_path / "legacy"
    candidate_root = tmp_path / "candidate"
    legacy_root.mkdir()
    candidate_root.mkdir()
    legacy_plan = legacy_root / "training_plan.duckdb"
    candidate_plan = candidate_root / "training_plan.duckdb"
    seed_plan(legacy_plan)
    seed_plan(candidate_plan)
    legacy_provider = BriefingProvider()
    with create_production_adaptive_daily_runtime(
        health_db_path=legacy_root / "health.duckdb",
        biomarkers_db_path=legacy_root / "biomarkers.duckdb",
        decisions_db_path=legacy_root / "decisions.duckdb",
        training_plan_db_path=legacy_plan,
        clock=RuntimeClock(),
        morning_briefing_provider=legacy_provider,
    ) as legacy:
        assert run_daily_decision_runtime(coordinator=legacy.coordinator) == 0
        legacy_decision = legacy.audit_repository.list_records()[0]
        legacy_rx = legacy.prescription_repository.list_records()[0]

    candidate_provider = BriefingProvider()
    options = fixture_options(candidate_root, candidate_provider)
    options["runtime_id_factory"] = lambda: "runtime-shadow"
    with create_production_daily_runtime(**options) as candidate:
        result = candidate.runtime.run_new_attempt(TARGET)
        assert result.status is RuntimeStatus.COMPLETED
        candidate_decision = candidate.decision_repository.get_by_id(result.decision_id)
    candidate_rx = DuckDbFinalSessionPrescriptionRepository(candidate_plan).list_records()[0]

    assert legacy_decision.context == candidate_decision.context
    assert legacy_decision.context.training.plan_id == "plan-cert"
    assert legacy_decision.context.training.planned_session_id == "plan-cert:2026-08-11"
    assert legacy_decision.policy_result == candidate_decision.policy_result
    assert legacy_decision.recommendation_plan == candidate_decision.recommendation_plan
    assert legacy_rx.plan_id == candidate_rx.plan_id == "plan-cert"
    assert legacy_rx.source_session == candidate_rx.source_session
    assert legacy_rx.disposition == candidate_rx.disposition
    assert legacy_rx.prescribed_kind == candidate_rx.prescribed_kind
    assert legacy_rx.prescribed_session_type == candidate_rx.prescribed_session_type
    assert legacy_rx.prescribed_duration_minutes == candidate_rx.prescribed_duration_minutes
    assert legacy_rx.prescribed_target_tss == candidate_rx.prescribed_target_tss
    assert legacy_rx.prescribed_intensity == candidate_rx.prescribed_intensity
    assert legacy_rx.reason_codes == candidate_rx.reason_codes
    assert legacy_rx.reconciliation_policy_version == candidate_rx.reconciliation_policy_version
