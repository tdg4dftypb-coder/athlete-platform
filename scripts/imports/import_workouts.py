from pathlib import Path

from application.activity_fact_backfill import recorded_activity_facts_from_persisted
from athlete.memory.activity_recorded import ActivityRecordedWriter
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from repositories.workout_repository import WorkoutRepository
from schema.athlete_memory_schema import AthleteMemorySchema
from schema.training_schema import TrainingSchema
from training.factories.activity_factory import ActivityFactory
from training.ingestion.fit_file_source_identity import FitFileSourceIdentity
from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer


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

    parser = FitParser()

    factory = ActivityFactory()

    analyzer = WorkoutAnalyzer()

    repository = WorkoutRepository(database)
    event_writer = ActivityRecordedWriter(AthleteMemoryRepository(database))
    identity_factory = FitFileSourceIdentity()

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

            if repository.exists(file.name):
                print(f"• {file.name} (analyzed facts exist)")
            else:
                parsed_activity = parser.parse(str(file))
                activity = factory.create(parsed_activity)
                workout = analyzer.analyze(activity)
                repository.save(
                    file_name=file.name,
                    workout=workout,
                )
                imported += 1
                print(f"✓ {file.name}")

            record = repository.get_persisted_record(file.name)
            if record is None:
                raise RuntimeError(
                    f"Persisted workout '{file.name}' could not be read after import"
                )
            result = event_writer.write(
                recorded_activity_facts_from_persisted(record),
                identity_factory.create(file),
            )
            if result.created:
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
