"""Production composition root for Adaptive Daily Decision Runtime."""
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional, Union

from application.adaptive_daily_coordinator import AdaptiveDailyRuntimeCoordinator
from application.training_plan_decision_context import TrainingPlanDecisionContextAdapter
from core.database import Database
from decision.daily_coordinator import DailyDecisionRuntimeCoordinator
from decision.persistence import (
    DuckDbDailyExecutionRepository,
    DuckDbDecisionAuditRecordRepository,
)
from decision.persistence.paths import get_default_decisions_db_path
from decision.production_composition import (
    ProductionDecisionRuntimeContainer,
    create_production_decision_runtime_application,
)
from decision.runtime_persistence_composition import (
    create_persisted_decision_runtime_application,
)
from decision.runtime_workflow import DecisionClock, SystemUtcDecisionClock
from performance_lab.provider import EmptyPerformanceTestHistoryProvider, PerformanceTestHistoryProvider
from training_plan.persistence.duckdb_repository import (
    DuckDbFinalSessionPrescriptionRepository,
    DuckDbTrainingPlanRepository,
)
from training_plan.persistence.paths import get_default_training_plan_db_path
from training_plan.provider import RepositoryTrainingPlanProvider


@dataclass
class ProductionAdaptiveDailyRuntimeContainer:
    """Managed container holding the adaptive coordinator and underlying repositories/connections."""

    coordinator: AdaptiveDailyRuntimeCoordinator
    daily_repository: DuckDbDailyExecutionRepository
    audit_repository: DuckDbDecisionAuditRecordRepository
    training_plan_repository: DuckDbTrainingPlanRepository
    prescription_repository: DuckDbFinalSessionPrescriptionRepository

    def close(self) -> None:
        """Explicitly release DuckDB connections and resources."""
        if self.daily_repository is not None and hasattr(self.daily_repository, "close"):
            self.daily_repository.close()
        if self.audit_repository is not None and hasattr(self.audit_repository, "close"):
            self.audit_repository.close()

    def __enter__(self) -> "ProductionAdaptiveDailyRuntimeContainer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_production_adaptive_daily_runtime(
    health_db_path: Optional[Union[str, Path]] = None,
    biomarkers_db_path: Optional[Union[str, Path]] = None,
    decisions_db_path: Optional[Union[str, Path]] = None,
    training_plan_db_path: Optional[Union[str, Path]] = None,
    performance_history_provider: Optional[PerformanceTestHistoryProvider] = None,
    clock: Optional[DecisionClock] = None,
    timezone_name: str = "Europe/Warsaw",
    lease_duration: timedelta = timedelta(minutes=15),
    morning_briefing_provider=None,
) -> ProductionAdaptiveDailyRuntimeContainer:
    """Builds a ProductionAdaptiveDailyRuntimeContainer wired to canonical database paths."""
    target_decisions_path = get_default_decisions_db_path(decisions_db_path)
    target_tp_path = get_default_training_plan_db_path(training_plan_db_path)

    # 1. Decision Repositories (shared DB connection)
    conn = Database(db_path=str(target_decisions_path)).connection
    daily_repo = DuckDbDailyExecutionRepository(conn=conn)
    audit_repo = DuckDbDecisionAuditRecordRepository(conn=conn)

    # 2. Training Plan Repositories
    tp_repo = DuckDbTrainingPlanRepository(db_path=target_tp_path)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=target_tp_path)
    tp_provider = RepositoryTrainingPlanProvider(repository=tp_repo)

    # 3. TrainingPlan-backed Decision Context Adapter
    from application.composition import build_morning_coach_use_case
    from biomarkers.composition import BiomarkersApplicationContext
    from biomarkers.dashboard import BiomarkersDashboardBuilder
    from morning_briefing.production_provider import ProductionMorningBriefingInputProvider
    from repositories.health_repository import HealthRepository

    target_health_path = str(health_db_path) if health_db_path is not None else "data/database/health.duckdb"
    db = Database(db_path=target_health_path)
    health_repo = HealthRepository(database=db)
    morning_coach_use_case = build_morning_coach_use_case(database=db, health_repository=health_repo)

    target_bio_path = str(biomarkers_db_path) if biomarkers_db_path is not None else "data/database/biomarkers.duckdb"
    bio_context = BiomarkersApplicationContext(db_path=target_bio_path)
    bio_builder = BiomarkersDashboardBuilder(
        repository=bio_context.repository,
        biomarker_registry=bio_context.registry,
        clock=bio_context.clock,
    )
    mb_provider = morning_briefing_provider or ProductionMorningBriefingInputProvider(
        morning_coach_use_case=morning_coach_use_case,
        biomarkers_dashboard_builder=bio_builder,
    )

    training_adapter = TrainingPlanDecisionContextAdapter(
        training_plan_provider=tp_provider,
        briefing_provider=mb_provider,
        default_timezone_name=timezone_name,
    )

    # 4. Inner Decision Runtime Container Factory
    def container_factory(fixed_gen):
        app = create_persisted_decision_runtime_application(
            morning_briefing_provider=mb_provider,
            performance_history_provider=performance_history_provider or EmptyPerformanceTestHistoryProvider(),
            repository=audit_repo,
            id_generator=fixed_gen,
            clock=clock,
            training_adapter=training_adapter,
        )
        return ProductionDecisionRuntimeContainer(
            app=app,
            database=db,
            biomarkers_context=bio_context,
        )

    # 5. Inner Stage 25 Decision Coordinator
    decision_coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock or SystemUtcDecisionClock(),
        timezone_name=timezone_name,
        lease_duration=lease_duration,
    )

    # 6. Outer Stage 26 Adaptive Daily Coordinator
    adaptive_coordinator = AdaptiveDailyRuntimeCoordinator(
        decision_coordinator=decision_coordinator,
        decision_audit_repository=audit_repo,
        training_plan_repository=tp_repo,
        prescription_repository=rx_repo,
    )

    return ProductionAdaptiveDailyRuntimeContainer(
        coordinator=adaptive_coordinator,
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        training_plan_repository=tp_repo,
        prescription_repository=rx_repo,
    )
