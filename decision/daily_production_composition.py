"""Production Composition Root for Automated Daily Decision Runtime.

Assembles resources, repositories, and coordinator for automated daily execution.
"""
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Callable, Optional, Union

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
from decision.runtime_workflow import DecisionClock, SystemUtcDecisionClock
from performance_lab.provider import PerformanceTestHistoryProvider


@dataclass
class ProductionDailyDecisionRuntimeContainer:
    """Managed container holding the daily coordinator and underlying repositories/connections."""
    coordinator: DailyDecisionRuntimeCoordinator
    daily_repository: DuckDbDailyExecutionRepository
    audit_repository: DuckDbDecisionAuditRecordRepository

    def close(self) -> None:
        """Explicitly release DuckDB connections and resources."""
        if self.daily_repository is not None and hasattr(self.daily_repository, "close"):
            self.daily_repository.close()
        if self.audit_repository is not None and hasattr(self.audit_repository, "close"):
            self.audit_repository.close()

    def __enter__(self) -> "ProductionDailyDecisionRuntimeContainer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_production_daily_decision_runtime(
    health_db_path: Optional[Union[str, Path]] = None,
    biomarkers_db_path: Optional[Union[str, Path]] = None,
    decisions_db_path: Optional[Union[str, Path]] = None,
    performance_history_provider: Optional[PerformanceTestHistoryProvider] = None,
    clock: Optional[DecisionClock] = None,
    timezone_name: str = "Europe/Warsaw",
    lease_duration: timedelta = timedelta(minutes=15),
) -> ProductionDailyDecisionRuntimeContainer:
    """Builds a ProductionDailyDecisionRuntimeContainer wired to canonical database paths."""
    target_decisions_path = get_default_decisions_db_path(decisions_db_path)

    # 1. Share a single DuckDB connection for Daily Ledger & Decision Audit Record Repositories
    conn = Database(db_path=str(target_decisions_path)).connection
    daily_repo = DuckDbDailyExecutionRepository(conn=conn)
    audit_repo = DuckDbDecisionAuditRecordRepository(conn=conn)

    # 2. Container factory for inner production runtime execution using FixedDecisionIdGenerator
    def container_factory(fixed_gen):
        return create_production_decision_runtime_application(
            health_db_path=health_db_path,
            biomarkers_db_path=biomarkers_db_path,
            decisions_db_path=target_decisions_path,
            performance_history_provider=performance_history_provider,
            id_generator=fixed_gen,
            clock=clock,
        )

    # 3. Daily Decision Runtime Coordinator
    coordinator = DailyDecisionRuntimeCoordinator(
        daily_repository=daily_repo,
        audit_repository=audit_repo,
        container_factory=container_factory,
        clock=clock or SystemUtcDecisionClock(),
        timezone_name=timezone_name,
        lease_duration=lease_duration,
    )

    return ProductionDailyDecisionRuntimeContainer(
        coordinator=coordinator,
        daily_repository=daily_repo,
        audit_repository=audit_repo,
    )
