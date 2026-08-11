"""Single owned production resource graph for the Stage 27 daily runtime candidate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from application.adaptive_daily_coordinator import (
    AdaptiveDailyRuntimeCoordinator,
    AdaptiveDailyRuntimeOutcome,
)
from application.composition import build_morning_coach_use_case
from application.standard_fit_ingestion import (
    StandardActivityFactSynchronizationService,
    StandardFitWorkoutIngestionService,
)
from application.training_plan_decision_context import TrainingPlanDecisionContextAdapter
from athlete.memory.activity_recorded import ActivityRecordedWriter
from athlete.memory.repository import AthleteMemoryRepository
from biomarkers.composition import BiomarkersApplicationContext
from biomarkers.dashboard import BiomarkersDashboardBuilder
from core.database import Database
from decision.daily_coordinator import DailyDecisionRuntimeCoordinator
from decision.daily_execution import DailyCoordinatorOutcome
from decision.persistence import DuckDbDailyExecutionRepository, DuckDbDecisionAuditRecordRepository
from decision.persistence.paths import get_default_decisions_db_path
from decision.runtime_persistence_composition import create_persisted_decision_runtime_application
from morning_briefing.production_provider import ProductionMorningBriefingInputProvider
from performance_lab.provider import EmptyPerformanceTestHistoryProvider
from production_runtime.adapters import (
    AssessmentSnapshotAdapter,
    CallablePhaseAdapter,
    IngestionRuntimePhaseAdapters,
    MorningBriefingProofAdapter,
    PersistedAssessmentSnapshotProvider,
    PublicationValidationAdapter,
    ReconciliationPolicySkipAdapter,
)
from production_runtime.clock import RuntimeClock, SystemUtcRuntimeClock
from production_runtime.coordinator import (
    MISSING_TRAINING_PLAN,
    ProductionDailyRuntime,
    RuntimePhaseError,
    RuntimePhaseOutcome,
)
from production_runtime.ingestion_slice import FitArtifactDiscovery, IngestionRuntimeSlice
from production_runtime.models import RuntimePhase
from production_runtime.paths import get_default_fit_activity_source_path, get_default_health_db_path
from production_runtime.paths import PROJECT_ROOT
from production_runtime.persistence import (
    DuckDbAssessmentSnapshotRepository,
    DuckDbRuntimeAuditRepository,
    get_default_runtime_audit_db_path,
)
from production_runtime.assessment_snapshot import (
    AssessmentSnapshotIntegrityError,
    AssessmentSnapshotUnavailableError,
)
from repositories.health_repository import HealthRepository
from repositories.workout_repository import WorkoutRepository
from schema.athlete_memory_schema import AthleteMemorySchema
from schema.training_schema import TrainingSchema
from training_plan.persistence.duckdb_repository import (
    DuckDbFinalSessionPrescriptionRepository,
    DuckDbTrainingPlanRepository,
)
from training_plan.persistence.paths import get_default_training_plan_db_path
from training_plan.provider import RepositoryTrainingPlanProvider


class _TargetDateDecisionClock:
    def __init__(self, target_date: date, timezone_name: str) -> None:
        local_noon = datetime.combine(target_date, time(12), ZoneInfo(timezone_name))
        self._value = local_noon.astimezone(ZoneInfo("UTC"))

    def now(self) -> datetime:
        return self._value


class _BorrowedDecisionContainer:
    def __init__(self, app) -> None:
        self.app = app
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None


@dataclass
class ProductionDailyRuntimeContainer:
    runtime: ProductionDailyRuntime
    health_database: Database
    biomarkers_context: BiomarkersApplicationContext
    decision_database: Database
    daily_repository: DuckDbDailyExecutionRepository
    decision_repository: DuckDbDecisionAuditRecordRepository
    assessment_snapshot_repository: DuckDbAssessmentSnapshotRepository

    def close(self) -> None:
        self.decision_database.close()
        self.health_database.close()
        repository = self.biomarkers_context.repository
        if hasattr(repository, "close"):
            repository.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def create_production_daily_runtime(
    *,
    target_local_date: date,
    health_db_path=None,
    biomarkers_db_path=None,
    decisions_db_path=None,
    training_plan_db_path=None,
    runtime_audit_db_path=None,
    fit_source_path=None,
    clock: RuntimeClock | None = None,
    runtime_id_factory=None,
    timezone_name: str = "Europe/Warsaw",
    briefing_input_provider=None,
) -> ProductionDailyRuntimeContainer:
    """Construct all five stores explicitly; caller owns the returned container."""
    health = Database(get_default_health_db_path(health_db_path))
    bio = None
    daily_repo = decision_repo = decision_database = None
    try:
        TrainingSchema(health).create()
        AthleteMemorySchema(health).create()
        workouts = WorkoutRepository(health)
        memory = AthleteMemoryRepository(health)
        runtime_clock = clock or SystemUtcRuntimeClock()
        runtime_path = get_default_runtime_audit_db_path(runtime_audit_db_path)
        audit = DuckDbRuntimeAuditRepository(runtime_path)
        snapshots = DuckDbAssessmentSnapshotRepository(runtime_path)

        bio_path = Path(biomarkers_db_path) if biomarkers_db_path else PROJECT_ROOT / "data/database/biomarkers.duckdb"
        if not bio_path.is_absolute():
            bio_path = PROJECT_ROOT / bio_path
        bio = BiomarkersApplicationContext(db_path=str(bio_path))
        if briefing_input_provider is None:
            coach = build_morning_coach_use_case(
                database=health, health_repository=HealthRepository(database=health)
            )
            bio_builder = BiomarkersDashboardBuilder(bio.repository, bio.registry, bio.clock)
            briefing_input_provider = ProductionMorningBriefingInputProvider(coach, bio_builder)
        frozen = PersistedAssessmentSnapshotProvider(
            briefing_input_provider, snapshots, runtime_clock
        )

        decision_clock = _TargetDateDecisionClock(target_local_date, timezone_name)
        decision_path = get_default_decisions_db_path(decisions_db_path)
        decision_database = Database(str(decision_path))
        daily_repo = DuckDbDailyExecutionRepository(conn=decision_database.connection)
        decision_repo = DuckDbDecisionAuditRecordRepository(conn=decision_database.connection)
        plan_path = get_default_training_plan_db_path(training_plan_db_path)
        plan_repo = DuckDbTrainingPlanRepository(plan_path)
        rx_repo = DuckDbFinalSessionPrescriptionRepository(plan_path)
        plan_provider = RepositoryTrainingPlanProvider(plan_repo)
        training_adapter = TrainingPlanDecisionContextAdapter(
            plan_provider, frozen, timezone_name
        )

        def decision_container(fixed_id):
            app = create_persisted_decision_runtime_application(
                morning_briefing_provider=frozen,
                performance_history_provider=EmptyPerformanceTestHistoryProvider(),
                repository=decision_repo,
                id_generator=fixed_id,
                clock=decision_clock,
                training_adapter=training_adapter,
            )
            return _BorrowedDecisionContainer(app)

        decision_coordinator = DailyDecisionRuntimeCoordinator(
            daily_repo, decision_repo, decision_container,
            clock=decision_clock, timezone_name=timezone_name,
        )
        adaptive = AdaptiveDailyRuntimeCoordinator(
            decision_coordinator, decision_repo, plan_repo, rx_repo
        )

        ingestion_slice = IngestionRuntimeSlice(
            audit, FitArtifactDiscovery(get_default_fit_activity_source_path(fit_source_path)),
            StandardFitWorkoutIngestionService(workouts),
            StandardActivityFactSynchronizationService(workouts, ActivityRecordedWriter(memory)),
            clock=runtime_clock,
        )
        ingestion = IngestionRuntimePhaseAdapters(ingestion_slice)

        def run_decision(context):
            frozen.bind(context)
            plan = plan_provider.get_plan_for_date(context.target_local_date)
            if plan is None:
                raise RuntimePhaseError(MISSING_TRAINING_PLAN)
            result = decision_coordinator.run_daily_if_needed()
            if result.outcome in (DailyCoordinatorOutcome.FAILED, DailyCoordinatorOutcome.SKIPPED_IN_PROGRESS):
                raise RuntimePhaseError("decision_unavailable")
            if result.decision_id is None:
                raise RuntimePhaseError("decision_unavailable")
            record = decision_repo.get_by_id(result.decision_id)
            if record is None:
                raise RuntimePhaseError("decision_not_resolvable")
            plan_id = record.context.training.plan_id
            if not plan_id:
                raise RuntimePhaseError(MISSING_TRAINING_PLAN)
            return RuntimePhaseOutcome(
                changed_state=result.outcome is DailyCoordinatorOutcome.EXECUTED,
                artifact_ids=(result.decision_id,), decision_id=result.decision_id,
                training_plan_id=plan_id,
            )

        def run_prescription(context):
            result = adaptive.run_adaptive_daily()
            if result.outcome is AdaptiveDailyRuntimeOutcome.MISSING_PLAN:
                raise RuntimePhaseError(MISSING_TRAINING_PLAN)
            if result.outcome in (AdaptiveDailyRuntimeOutcome.FAILED, AdaptiveDailyRuntimeOutcome.SKIPPED_IN_PROGRESS):
                raise RuntimePhaseError("prescription_unavailable")
            record = decision_repo.get_by_id(result.decision_id) if result.decision_id else None
            plan_id = record.context.training.plan_id if record else None
            if not plan_id or not result.prescription_id:
                raise RuntimePhaseError("prescription_not_resolvable")
            return RuntimePhaseOutcome(
                changed_state=result.outcome is AdaptiveDailyRuntimeOutcome.EXECUTED,
                artifact_ids=(plan_id, result.prescription_id), training_plan_id=plan_id,
                prescription_id=result.prescription_id,
            )

        def assessment_resolves(runtime_id, artifact_id, target_date):
            try:
                snapshot = snapshots.get_by_runtime_id(runtime_id)
            except AssessmentSnapshotIntegrityError as error:
                raise RuntimePhaseError("assessment_snapshot_corrupt", str(error)) from error
            except AssessmentSnapshotUnavailableError as error:
                raise RuntimePhaseError("assessment_snapshot_unavailable", str(error)) from error
            if snapshot is None:
                raise RuntimePhaseError("assessment_snapshot_missing")
            if snapshot.artifact_id != artifact_id or snapshot.target_local_date != target_date:
                raise RuntimePhaseError("assessment_snapshot_corrupt")
            return True

        adapters = {
            RuntimePhase.INGESTION: CallablePhaseAdapter(ingestion.ingestion),
            RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION: CallablePhaseAdapter(ingestion.facts),
            RuntimePhase.RECONCILIATION: ReconciliationPolicySkipAdapter(),
            RuntimePhase.ASSESSMENT: AssessmentSnapshotAdapter(frozen),
            RuntimePhase.DECISION: CallablePhaseAdapter(run_decision),
            RuntimePhase.PLAN_PRESCRIPTION: CallablePhaseAdapter(run_prescription),
            RuntimePhase.MORNING_BRIEFING: MorningBriefingProofAdapter(frozen),
            RuntimePhase.PUBLICATION: PublicationValidationAdapter(
                lambda item: decision_repo.get_by_id(item) is not None,
                lambda item: plan_repo.get_by_id(item) is not None,
                lambda item: rx_repo.get_by_id(item) is not None,
                assessment_resolves,
            ),
        }
        runtime = ProductionDailyRuntime(
            audit, adapters, clock=runtime_clock, runtime_id_factory=runtime_id_factory,
            timezone_name=timezone_name,
        )
        return ProductionDailyRuntimeContainer(
            runtime, health, bio, decision_database, daily_repo, decision_repo, snapshots
        )
    except Exception:
        if decision_database is not None:
            decision_database.close()
        health.close()
        if bio is not None and hasattr(bio.repository, "close"):
            bio.repository.close()
        raise
