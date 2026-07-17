from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from decision.engine import DecisionEngine

from athlete.state_builder import AthleteStateBuilder

from repositories.health_repository import HealthRepository
from repositories.workout_repository import WorkoutRepository

from engines.context_builder import ContextBuilder

from recovery.engine import RecoveryEngine
from performance.engine import PerformanceEngine

from planner.engine import PlannerEngine
from workout.builders.workout_builder import WorkoutBuilder

from execution.engine import ExecutionEngine

from training.history.workout_history_builder import (
    WorkoutHistoryBuilder,
)

from health.engine import HealthEngine


def main():

    #
    # Athlete
    #

    repository = HealthRepository()

    history = repository.load_daily()

    context = ContextBuilder().build(history)

    athlete = AthleteStateBuilder().build(

        health=HealthEngine().analyze(context),

        context=context,

        recovery=RecoveryEngine().analyze(context),

        performance=PerformanceEngine().analyze(),

    )

    decision = DecisionEngine().decide(athlete)

    planner = PlannerEngine()

    planned = planner.build(decision)

    workout = WorkoutBuilder().build(

        decision,

        planned,

    )

    #
    # Last workout
    #

    workout_history = WorkoutHistoryBuilder()

    last = workout_history.last_days(1)

    if last.count == 0:

        print("No workout.")

        return

    activity = last.workouts[0]

    #
    # Compare
    #

    execution = ExecutionEngine().analyze(

        workout,

        activity,

    )

    print()
    print("=" * 72)
    print("WORKOUT EXECUTION")
    print("=" * 72)
    print()

    print("Workout")
    print("-" * 72)

    print(workout.name)

    print()

    print("Duration")
    print("-" * 72)

    print(f"Planned : {execution.planned_duration} min")
    print(f"Actual  : {execution.executed_duration} min")
    print(f"Score   : {execution.duration_score:.1f}%")

    print()

    print("TSS")
    print("-" * 72)

    print(f"Planned : {execution.planned_tss:.1f}")
    print(f"Actual  : {execution.executed_tss:.1f}")
    print(f"Score   : {execution.tss_score:.1f}%")

    print()

    print("Overall")
    print("-" * 72)

    print(f"Score   : {execution.overall_score:.1f}%")

    print(
        "Status  :",
        "COMPLETED"
        if execution.completed
        else "NOT COMPLETED",
    )

    print()

    if execution.reasons:

        print("Reasons")
        print("-" * 72)

        for reason in execution.reasons:

            print("•", reason)

    print()
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()