"""Date-bounded maintenance command for canonical historical activity facts."""
import argparse
from datetime import date
from pathlib import Path

from application.activity_fact_backfill import HistoricalActivityFactBackfill
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from repositories.workout_repository import WorkoutRepository


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Backfill persisted workouts as canonical ACTIVITY_RECORDED facts.",
    )
    parser.add_argument("database_path", type=Path)
    parser.add_argument("fit_directory", type=Path)
    parser.add_argument("--start-date", type=date.fromisoformat, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create events. Without this flag the command is a dry run.",
    )
    arguments = parser.parse_args(argv)

    database = Database(arguments.database_path)
    try:
        report = HistoricalActivityFactBackfill(
            WorkoutRepository(database),
            AthleteMemoryRepository(database),
            arguments.fit_directory,
        ).run(
            arguments.start_date,
            arguments.end_date,
            dry_run=not arguments.apply,
        )
    finally:
        database.close()

    print("mode:", "apply" if arguments.apply else "dry-run")
    for field in report.__dataclass_fields__:
        print(f"{field}:", getattr(report, field))


if __name__ == "__main__":
    main()
