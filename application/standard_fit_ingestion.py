"""Reusable application services behind the standard FIT import path."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from application.activity_fact_backfill import recorded_activity_facts_from_persisted
from athlete.memory.activity_recorded import ActivityRecordedWriter
from repositories.workout_repository import WorkoutRepository
from training.analysis.workout_analyzer import WorkoutAnalyzer
from training.factories.activity_factory import ActivityFactory
from training.ingestion.fit_file_source_identity import FitFileSourceIdentity
from training.parsers.fit_parser import FitParser


class MissingPersistedWorkoutError(RuntimeError):
    """A discovered FIT artifact has no analysed workout row to synchronize."""


@dataclass(frozen=True)
class WorkoutIngestionResult:
    file_name: str
    persisted: bool


@dataclass(frozen=True)
class ActivityFactSynchronizationResult:
    file_name: str
    source_type: str
    source_key: str
    event_id: str
    created: bool


class StandardFitWorkoutIngestionService:
    """Persist analysed workout facts using the established standard pipeline."""

    def __init__(
        self,
        repository: WorkoutRepository,
        parser: FitParser | None = None,
        activity_factory: ActivityFactory | None = None,
        analyzer: WorkoutAnalyzer | None = None,
    ) -> None:
        self._repository = repository
        self._parser = parser or FitParser()
        self._activity_factory = activity_factory or ActivityFactory()
        self._analyzer = analyzer or WorkoutAnalyzer()

    def ingest(self, fit_path: Path, *, storage_key: str | None = None) -> WorkoutIngestionResult:
        record_key = storage_key or fit_path.name
        if self._repository.exists(record_key):
            return WorkoutIngestionResult(record_key, persisted=False)
        parsed_activity = self._parser.parse(str(fit_path))
        activity = self._activity_factory.create(parsed_activity)
        workout = self._analyzer.analyze(activity)
        self._repository.save(file_name=record_key, workout=workout)
        return WorkoutIngestionResult(record_key, persisted=True)


class StandardActivityFactSynchronizationService:
    """Verify or repair canonical ACTIVITY_RECORDED for one standard FIT artifact."""

    def __init__(
        self,
        workout_repository: WorkoutRepository,
        writer: ActivityRecordedWriter,
        identity_factory: FitFileSourceIdentity | None = None,
    ) -> None:
        self._workouts = workout_repository
        self._writer = writer
        self._identity_factory = identity_factory or FitFileSourceIdentity()

    def persisted_record(self, record_key: str):
        return self._workouts.get_persisted_record(record_key)

    def synchronize(self, fit_path: Path, *, record_key: str | None = None,
                    identity=None) -> ActivityFactSynchronizationResult:
        persisted_key = record_key or fit_path.name
        record = self._workouts.get_persisted_record(persisted_key)
        if record is None:
            raise MissingPersistedWorkoutError(
                f"Persisted workout '{persisted_key}' is unavailable for fact synchronization"
            )
        identity = identity or self._identity_factory.create(fit_path)
        result = self._writer.write(
            recorded_activity_facts_from_persisted(record),
            identity,
        )
        return ActivityFactSynchronizationResult(
            file_name=persisted_key,
            source_type=identity.provider,
            source_key=identity.external_id,
            event_id=result.event.event_id,
            created=result.created,
        )
