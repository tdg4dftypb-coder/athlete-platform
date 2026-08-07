"""Production Composition Root for Decision Intelligence 2.0 Runtime.

Assembles real Athlete Platform data sources and handles resource lifecycle.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Union

from biomarkers.composition import BiomarkersApplicationContext
from biomarkers.dashboard import BiomarkersDashboardBuilder
from core.database import Database
from decision.persistence import DuckDbDecisionAuditRecordRepository
from decision.persistence.paths import get_default_decisions_db_path
from decision.runtime_persistence_composition import (
    DecisionRuntimeApplication,
    create_persisted_decision_runtime_application,
)
from morning_briefing.production_provider import ProductionMorningBriefingInputProvider
from performance_lab.provider import (
    EmptyPerformanceTestHistoryProvider,
    PerformanceTestHistoryProvider,
)
from repositories.health_repository import HealthRepository


@dataclass
class ProductionDecisionRuntimeContainer:
    """Managed container holding the persisted decision application and underlying resources."""
    app: DecisionRuntimeApplication
    database: Database
    biomarkers_context: BiomarkersApplicationContext

    def close(self) -> None:
        """Explicitly release DuckDB connections and resources."""
        if self.database is not None:
            self.database.close()
        if (
            self.biomarkers_context is not None
            and getattr(self.biomarkers_context, "repository", None) is not None
            and hasattr(self.biomarkers_context.repository, "close")
        ):
            self.biomarkers_context.repository.close()

    def __enter__(self) -> "ProductionDecisionRuntimeContainer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_production_decision_runtime_application(
    health_db_path: Optional[Union[str, Path]] = None,
    biomarkers_db_path: Optional[Union[str, Path]] = None,
    decisions_db_path: Optional[Union[str, Path]] = None,
    performance_history_provider: Optional[PerformanceTestHistoryProvider] = None,
    id_generator: Optional[Callable[[], str]] = None,
    clock: Optional[Callable[[], Any]] = None,
) -> ProductionDecisionRuntimeContainer:
    """Builds a ProductionDecisionRuntimeContainer wired with real Athlete Platform data sources."""
    from application.composition import build_morning_coach_use_case

    # 1. Health DB & Morning Coach UseCase
    target_health_path = str(health_db_path) if health_db_path is not None else "data/database/health.duckdb"
    db = Database(db_path=target_health_path)
    health_repo = HealthRepository(database=db)
    morning_coach_use_case = build_morning_coach_use_case(database=db, health_repository=health_repo)

    # 2. Persisted Biomarkers Source (DuckDB)
    target_bio_path = str(biomarkers_db_path) if biomarkers_db_path is not None else "data/database/biomarkers.duckdb"
    bio_context = BiomarkersApplicationContext(db_path=target_bio_path)
    bio_builder = BiomarkersDashboardBuilder(
        repository=bio_context.repository,
        biomarker_registry=bio_context.registry,
        clock=bio_context.clock,
    )

    # 3. Production Morning Briefing Provider
    mb_provider = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=morning_coach_use_case,
        biomarkers_dashboard_builder=bio_builder,
    )

    # 4. Performance Lab History Provider (Default to Empty/UNAVAILABLE if no persisted store exists)
    perf_provider = performance_history_provider or EmptyPerformanceTestHistoryProvider()

    # 5. DuckDB Decision Audit Record Repository
    target_decisions_path = get_default_decisions_db_path(decisions_db_path)
    repo = DuckDbDecisionAuditRecordRepository(db_path=str(target_decisions_path))

    # 6. Persisted Decision Runtime Application
    app = create_persisted_decision_runtime_application(
        morning_briefing_provider=mb_provider,
        performance_history_provider=perf_provider,
        repository=repo,
        id_generator=id_generator,
        clock=clock,
    )

    return ProductionDecisionRuntimeContainer(
        app=app,
        database=db,
        biomarkers_context=bio_context,
    )
