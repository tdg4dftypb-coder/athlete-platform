"""Inactive composition seam for a future controlled DIG.5 runtime gate."""
from application.standard_fit_ingestion import (
    StandardActivityFactSynchronizationService,
    StandardFitWorkoutIngestionService,
)
from athlete.memory.activity_recorded import ActivityRecordedWriter
from athlete.memory.repository import AthleteMemoryRepository
from repositories.workout_repository import WorkoutRepository

from .discovery import ZwiftFitArtifactDiscovery
from .persistence import ZwiftFitRepository
from .service import ZwiftFitSyncService


def build_zwift_fit_sync_service(connection, source_directory):
    """Compose only; callers explicitly initialize schema and choose execution time."""
    workouts = WorkoutRepository(connection)
    return ZwiftFitSyncService(
        ZwiftFitArtifactDiscovery(source_directory),
        StandardFitWorkoutIngestionService(workouts),
        StandardActivityFactSynchronizationService(
            workouts,
            ActivityRecordedWriter(AthleteMemoryRepository(connection)),
        ),
        ZwiftFitRepository(connection.connection),
    )
