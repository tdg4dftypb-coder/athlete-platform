"""Explicit HealthKit ingestion composition with no import-time I/O."""
from pathlib import Path

from core.database import Database
from health_ingestion.persistence import HealthKitIngestionSchema, HealthKitRepository
from health_ingestion.service import HealthKitIngestionService
from production_runtime.paths import get_default_health_db_path


def initialize_healthkit_ingestion_schema(db_path=None) -> Path:
    """Explicit operator-controlled additive schema initialization."""

    resolved = get_default_health_db_path(db_path)
    database = Database(resolved)
    try:
        HealthKitIngestionSchema.create(database)
    finally:
        database.close()
    return resolved


def build_healthkit_ingestion_service(database: Database) -> HealthKitIngestionService:
    """Build against an already-open, explicitly initialized Health database."""

    return HealthKitIngestionService(HealthKitRepository(database))
