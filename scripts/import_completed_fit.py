import argparse
from datetime import timedelta
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DATABASE_PATH = ROOT / "data/database/health.duckdb"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.post_workout_recording import PostWorkoutRecordingService
from athlete.memory.models import DateRange
from athlete.memory.reader import AthleteMemoryReader
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.writer import AthleteMemoryWriter
from core.database import Database
from decision.models import DecisionResult
from decision.sports import Sport
from pipeline.post_workout import PostWorkoutPipeline
from planner.catalog.registry import TrainingRecipeRegistry
from planner.dsl.compiler import DSLCompiler
from planner.dsl.parser import DSLParser
from planner.models import PlannedWorkout
from schema.athlete_memory_schema import AthleteMemorySchema
from training.factories.activity_factory import ActivityFactory
from training.parsers.fit_parser import FitParser
from workout.builders.workout_builder import WorkoutBuilder


def available_plan_ids() -> tuple[str, ...]:
    return tuple(
        recipe.id
        for recipe in TrainingRecipeRegistry().all()
    )


def build_workout(plan_id: str):
    """Compile one explicitly selected catalog recipe to a domain Workout."""

    recipe = TrainingRecipeRegistry().by_id(plan_id)
    dsl_workout = DSLParser().build(recipe)
    blocks = DSLCompiler().compile(dsl_workout)
    planned = PlannedWorkout(
        name=dsl_workout.name,
        sport=Sport.CYCLING.value,
        target_tss=recipe.prescription.target_tss,
        estimated_duration=sum(block.duration for block in blocks) // 60,
        blocks=blocks,
    )
    decision = DecisionResult(
        sport=Sport.CYCLING,
        recommendation=recipe.identity.workout_type,
        duration=planned.estimated_duration,
        target_tss=planned.target_tss,
        intensity="catalog import",
        reasons=[],
    )

    return WorkoutBuilder().build(decision, planned)


def import_completed_fit(
    fit_path: Path,
    database_path: Path,
    plan_id: str,
):
    """Record one FIT activity against an explicitly selected existing plan."""

    if database_path.resolve() == PRODUCTION_DATABASE_PATH:
        raise ValueError(
            "Refusing to import into data/database/health.duckdb. "
            "Use an explicitly selected temporary DuckDB database.",
        )

    parsed_activity = FitParser().parse(str(fit_path))
    activity = ActivityFactory().create(parsed_activity)
    workout = build_workout(plan_id)
    database = Database(database_path)

    try:
        AthleteMemorySchema(database).create()
        repository = AthleteMemoryRepository(database)
        service = PostWorkoutRecordingService(
            PostWorkoutPipeline(),
            AthleteMemoryWriter(repository),
        )

        try:
            result = service.record(workout, activity)
        except duckdb.ConstraintException:
            print(
                "SKIPPED: already imported "
                f"(source_key={activity.start.isoformat()})",
            )
            return None

        snapshot = AthleteMemoryReader(repository).read(
            _activity_period(activity),
        )
        if len(snapshot.workout_observations) != 1:
            raise RuntimeError("Imported activity was not projected into Athlete Memory")

        return result
    finally:
        database.close()


def _activity_period(activity):
    return DateRange(
        start=activity.start,
        end=activity.end + timedelta(microseconds=1),
    )


def _print_result(result) -> None:
    event = result.event
    execution = result.post_workout.execution

    print(f"event_id: {event.event_id}")
    print(f"event_type: {event.event_type.value}")
    print(f"occurred_at: {event.occurred_at.isoformat()}")
    print(f"source_key: {event.source_key}")
    print(f"plan: {result.post_workout.workout.name}")
    print(f"activity_duration: {result.post_workout.activity.duration} seconds")
    print(f"tss: {result.post_workout.workout_summary.tss}")
    print(f"completion_score: {execution.completion_score}")
    print(f"execution_score: {execution.execution_score}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Record one completed FIT activity in a selected DuckDB database.",
    )
    parser.add_argument("fit_path", type=Path)
    parser.add_argument("database_path", type=Path)
    parser.add_argument("plan_id", choices=available_plan_ids())
    arguments = parser.parse_args(argv)

    result = import_completed_fit(
        arguments.fit_path,
        arguments.database_path,
        arguments.plan_id,
    )
    if result is not None:
        _print_result(result)


if __name__ == "__main__":
    main()
