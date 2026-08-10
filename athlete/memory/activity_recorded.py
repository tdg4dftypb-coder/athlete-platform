"""Canonical factual activity event contract and idempotent writer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType
from athlete.memory.repository import (
    AthleteMemoryRepository,
    DuplicateSourceIdentityError,
)
from training.ingestion.source_identity import SourceIdentity


@dataclass(frozen=True)
class RecordedActivityFacts:
    start: datetime
    end: datetime
    sport: str | None
    duration: int | None
    distance: float | None
    calories: int | None
    tss: float | None = None
    normalized_power: float | None = None
    intensity_factor: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.start, datetime) or not isinstance(self.end, datetime):
            raise TypeError("start and end must be datetime instances")
        if self.end < self.start:
            raise ValueError("end must not be before start")
        if self.sport is not None and not self.sport.strip():
            raise ValueError("sport must be non-empty when present")
        numeric_fields = (
            "duration",
            "distance",
            "calories",
            "tss",
            "normalized_power",
            "intensity_factor",
        )
        for name in numeric_fields:
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must not be negative")


class ActivityRecordedSerializer:
    SCHEMA_VERSION = 1

    def serialize(self, facts: RecordedActivityFacts) -> dict:
        if not isinstance(facts, RecordedActivityFacts):
            raise TypeError("facts must be RecordedActivityFacts")
        return {
            "schema_version": self.SCHEMA_VERSION,
            "activity": {
                "start": facts.start.isoformat(),
                "end": facts.end.isoformat(),
                "sport": facts.sport,
                "duration": facts.duration,
                "distance": facts.distance,
                "calories": facts.calories,
            },
            "workout_summary": {
                "tss": facts.tss,
                "normalized_power": facts.normalized_power,
                "intensity_factor": facts.intensity_factor,
            },
        }


@dataclass(frozen=True)
class ActivityRecordedWriteResult:
    event: AthleteMemoryEvent
    created: bool


class ActivityRecordedWriter:
    def __init__(
        self,
        repository: AthleteMemoryRepository,
        serializer: ActivityRecordedSerializer | None = None,
    ) -> None:
        self._repository = repository
        self._serializer = serializer or ActivityRecordedSerializer()

    def write(
        self,
        facts: RecordedActivityFacts,
        source_identity: SourceIdentity,
    ) -> ActivityRecordedWriteResult:
        existing = self._repository.get_by_source_identity(
            AthleteMemoryEventType.ACTIVITY_RECORDED,
            source_identity.provider,
            source_identity.external_id,
        )
        if existing is not None:
            return ActivityRecordedWriteResult(existing, created=False)

        event = AthleteMemoryEvent(
            event_id=str(uuid4()),
            occurred_at=facts.end,
            event_type=AthleteMemoryEventType.ACTIVITY_RECORDED,
            source_type=source_identity.provider,
            source_key=source_identity.external_id,
            schema_version=self._serializer.SCHEMA_VERSION,
            payload=self._serializer.serialize(facts),
        )
        try:
            self._repository.append(event)
        except DuplicateSourceIdentityError:
            existing = self._repository.get_by_source_identity(
                AthleteMemoryEventType.ACTIVITY_RECORDED,
                source_identity.provider,
                source_identity.external_id,
            )
            if existing is None:
                raise
            return ActivityRecordedWriteResult(existing, created=False)
        return ActivityRecordedWriteResult(event, created=True)
