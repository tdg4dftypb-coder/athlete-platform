from pathlib import Path

from application.standard_fit_ingestion import (
    StandardActivityFactSynchronizationService,
    StandardFitWorkoutIngestionService,
)
from athlete.memory.activity_recorded import ActivityRecordedWriter
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from repositories.workout_repository import WorkoutRepository
from schema.athlete_memory_schema import AthleteMemorySchema
from schema.training_schema import TrainingSchema


WORKOUTS = Path(
    "/Users/marsm0wa/Documents/Zwift/Activities"
)


def import_workouts(
    workouts_directory: Path = WORKOUTS,
    database_path: Path = Path("data/database/health.duckdb"),
) -> tuple[int, int, int]:

    database = Database(database_path)
    TrainingSchema(database).create()
    AthleteMemorySchema(database).create()

    repository = WorkoutRepository(database)
    ingestion = StandardFitWorkoutIngestionService(repository)
    fact_synchronization = StandardActivityFactSynchronizationService(
        repository,
        ActivityRecordedWriter(AthleteMemoryRepository(database)),
    )

    files = sorted(
        workouts_directory.glob("*.fit")
    )

    print()

    print(f"Importing {len(files)} workouts...")

    print()

    imported = 0
    factual_created = 0
    factual_existing = 0

    try:
        for file in files:

            ingestion_result = ingestion.ingest(file)
            if not ingestion_result.persisted:
                print(f"• {file.name} (analyzed facts exist)")
            else:
                imported += 1
                print(f"✓ {file.name}")

            sync_result = fact_synchronization.synchronize(file)
            if sync_result.created:
                factual_created += 1
            else:
                factual_existing += 1
    finally:
        database.close()

    return imported, factual_created, factual_existing


def main():
    imported, factual_created, factual_existing = import_workouts()
    print("Imported workouts       :", imported)
    print("Activity facts created  :", factual_created)
    print("Activity facts existing :", factual_existing)


if __name__ == "__main__":
    main()
