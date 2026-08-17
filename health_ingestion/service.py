"""Application ingestion service; HTTP never writes SQL directly."""
from datetime import datetime, timezone
import json

from health_ingestion.models import HealthKitBatch, HealthKitBatchAck
from health_ingestion.persistence import HealthKitRepository


class HealthKitIngestionService:
    def __init__(self, repository: HealthKitRepository) -> None:
        self._repository = repository

    def ingest(self, payload: dict) -> HealthKitBatchAck:
        batch, rejected_ids = HealthKitBatch.parse_partial(payload)
        existing = self._repository.existing_batch(batch)
        if existing is not None:
            return HealthKitBatchAck(
                batch.batch_id, 0, len(batch.records), existing[3],
                tuple(json.loads(existing[4])),
                existing[5].replace(tzinfo=timezone.utc),
            )
        received_at = datetime.now(timezone.utc)
        accepted, duplicate = self._repository.persist(batch, received_at, rejected_ids)
        return HealthKitBatchAck(
            batch.batch_id, accepted, duplicate, len(rejected_ids), rejected_ids,
            received_at,
        )
