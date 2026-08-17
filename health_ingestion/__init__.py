"""Versioned HealthKit ingestion boundary."""

from health_ingestion.models import (
    HEALTHKIT_CONTRACT_VERSION,
    MAX_HEALTHKIT_BATCH_RECORDS,
    HealthKitBatch,
    HealthKitBatchAck,
    HealthKitSourceRecord,
)
from health_ingestion.persistence import HealthKitIngestionSchema, HealthKitRepository
from health_ingestion.service import HealthKitIngestionService
from health_ingestion.composition import (
    build_healthkit_ingestion_service,
    initialize_healthkit_ingestion_schema,
)

__all__ = [
    "HEALTHKIT_CONTRACT_VERSION",
    "MAX_HEALTHKIT_BATCH_RECORDS",
    "HealthKitBatch",
    "HealthKitBatchAck",
    "HealthKitSourceRecord",
    "HealthKitIngestionSchema",
    "HealthKitRepository",
    "HealthKitIngestionService",
    "build_healthkit_ingestion_service",
    "initialize_healthkit_ingestion_schema",
]
