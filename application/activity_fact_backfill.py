"""Explicit historical projection from persisted workout facts to Athlete Memory."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from athlete.memory.activity_recorded import (
    ActivityRecordedWriter,
    RecordedActivityFacts,
)
from athlete.memory.models import AthleteMemoryEventType
from athlete.memory.repository import AthleteMemoryRepository
from repositories.workout_repository import PersistedWorkoutRecord, WorkoutRepository
from training.ingestion.fit_file_source_identity import FitFileSourceIdentity


@dataclass(frozen=True)
class ActivityFactBackfillReport:
    scanned: int = 0
    eligible: int = 0
    identity_matched: int = 0
    already_present: int = 0
    would_create: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0


class HistoricalActivityFactBackfill:
    def __init__(
        self,
        workout_repository: WorkoutRepository,
        event_repository: AthleteMemoryRepository,
        fit_directory: Path,
    ) -> None:
        self._workouts = workout_repository
        self._events = event_repository
        self._fit_directory = fit_directory
        self._identity = FitFileSourceIdentity()
        self._writer = ActivityRecordedWriter(event_repository)

    def run(
        self,
        start_date: date,
        end_date: date,
        dry_run: bool = True,
    ) -> ActivityFactBackfillReport:
        if type(start_date) is not date or type(end_date) is not date:
            raise TypeError("start_date and end_date must be date instances")
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")

        records = self._workouts.persisted_records_between(
            datetime.combine(start_date, time.min),
            datetime.combine(end_date + timedelta(days=1), time.min),
        )
        counts = {
            "scanned": len(records),
            "eligible": 0,
            "identity_matched": 0,
            "already_present": 0,
            "would_create": 0,
            "created": 0,
            "skipped": 0,
            "failed": 0,
        }

        for record in records:
            try:
                facts = recorded_activity_facts_from_persisted(record)
                counts["eligible"] += 1
                matches = [
                    path
                    for path in self._fit_directory.rglob("*")
                    if path.is_file() and path.name == record.file_name
                ]
                if len(matches) != 1:
                    counts["skipped"] += 1
                    continue
                source_identity = self._identity.create(matches[0])
                counts["identity_matched"] += 1

                existing = self._events.get_by_source_identity(
                    AthleteMemoryEventType.ACTIVITY_RECORDED,
                    source_identity.provider,
                    source_identity.external_id,
                )
                if existing is not None:
                    counts["already_present"] += 1
                    continue
                if dry_run:
                    counts["would_create"] += 1
                    continue

                result = self._writer.write(facts, source_identity)
                if result.created:
                    counts["created"] += 1
                else:
                    counts["already_present"] += 1
            except (TypeError, ValueError):
                counts["skipped"] += 1
            except Exception:
                counts["failed"] += 1

        return ActivityFactBackfillReport(**counts)


def _legacy_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("legacy timestamp must be a datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def recorded_activity_facts_from_persisted(
    record: PersistedWorkoutRecord,
) -> RecordedActivityFacts:
    return RecordedActivityFacts(
        start=_legacy_utc(record.start_time),
        end=_legacy_utc(record.end_time),
        sport=record.sport,
        duration=record.duration,
        distance=record.distance,
        calories=record.calories,
        tss=record.tss,
        normalized_power=record.normalized_power,
        intensity_factor=record.intensity_factor,
    )
