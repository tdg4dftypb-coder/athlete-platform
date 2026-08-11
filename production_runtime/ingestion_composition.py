"""Owned production resources for the Stage 27.3 ingestion runtime slice."""
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Union

from application.standard_fit_ingestion import (
    StandardActivityFactSynchronizationService,
    StandardFitWorkoutIngestionService,
)
from athlete.memory.activity_recorded import ActivityRecordedWriter
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from production_runtime.clock import RuntimeClock
from production_runtime.ingestion_slice import FitArtifactDiscovery, IngestionRuntimeSlice
from production_runtime.models import ProductionDailyRuntimeResult
from production_runtime.paths import (
    get_default_fit_activity_source_path,
    get_default_health_db_path,
)
from production_runtime.persistence import (
    DuckDbRuntimeAuditRepository,
    get_default_runtime_audit_db_path,
)
from repositories.workout_repository import WorkoutRepository
from schema.athlete_memory_schema import AthleteMemorySchema
from schema.training_schema import TrainingSchema


@dataclass
class ProductionIngestionRuntimeSliceContainer:
    runtime_slice: IngestionRuntimeSlice
    database: Database
    audit_repository: DuckDbRuntimeAuditRepository

    def close(self) -> None:
        self.database.close()

    def __enter__(self) -> "ProductionIngestionRuntimeSliceContainer":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def create_production_ingestion_runtime_slice(
    health_db_path: Union[str, Path, None] = None,
    runtime_audit_db_path: Union[str, Path, None] = None,
    fit_source_path: Union[str, Path, None] = None,
    clock: RuntimeClock | None = None,
    runtime_id_factory: Callable[[], str] | None = None,
) -> ProductionIngestionRuntimeSliceContainer:
    database = Database(get_default_health_db_path(health_db_path))
    try:
        TrainingSchema(database).create()
        AthleteMemorySchema(database).create()
        workouts = WorkoutRepository(database)
        memory = AthleteMemoryRepository(database)
        audit = DuckDbRuntimeAuditRepository(
            get_default_runtime_audit_db_path(runtime_audit_db_path)
        )
        runtime_slice = IngestionRuntimeSlice(
            audit_repository=audit,
            discovery=FitArtifactDiscovery(
                get_default_fit_activity_source_path(fit_source_path)
            ),
            ingestion=StandardFitWorkoutIngestionService(workouts),
            fact_synchronization=StandardActivityFactSynchronizationService(
                workouts,
                ActivityRecordedWriter(memory),
            ),
            clock=clock,
            runtime_id_factory=runtime_id_factory,
        )
        return ProductionIngestionRuntimeSliceContainer(runtime_slice, database, audit)
    except Exception:
        database.close()
        raise


def run_production_ingestion_runtime_slice(
    target_local_date: date,
    **composition_options,
) -> ProductionDailyRuntimeResult:
    """Run one new bounded attempt and always close the owned health database."""
    with create_production_ingestion_runtime_slice(**composition_options) as container:
        return container.runtime_slice.run_new_attempt(target_local_date)
