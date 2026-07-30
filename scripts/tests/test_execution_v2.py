from pathlib import Path

from athlete.state_builder import AthleteStateBuilder
from decision.engine import DecisionEngine
from engines.context_builder import ContextBuilder
from execution.context import ExecutionContext
from execution.engine import ExecutionEngine
from health.engine import HealthEngine
from performance.engine import PerformanceEngine
from planner.engine import PlannerEngine
from recovery.engine import RecoveryEngine
from repositories.health_repository import HealthRepository
from timeline.builder import TimelineBuilder
from training.analysis.workout_analyzer import WorkoutAnalyzer
from training.factories.activity_factory import ActivityFactory
from training.parsers.fit_parser import FitParser
from workout.builders.workout_builder import WorkoutBuilder


def score(value: float | None) -> str:

    return f"{value:.1f}%" if value is not None else "n/a"


def main():

    history = HealthRepository().load_daily()
    context = ContextBuilder().build(history)

    parsed_activity = FitParser().parse(
        str(
            sorted(
                Path(
                    "/Users/marsm0wa/Documents/Zwift/Activities"
                ).glob("*.fit")
            )[-1]
        )
    )

    activity = ActivityFactory().create(parsed_activity)
    summary = WorkoutAnalyzer().analyze(activity)

    athlete = AthleteStateBuilder().build(
        health=HealthEngine().analyze(context),
        context=context,
        recovery=RecoveryEngine().analyze(context),
        performance=PerformanceEngine().analyze(),
        workout=summary,
    )

    decision = DecisionEngine().decide(athlete)
    planned = PlannerEngine().build(decision, athlete)
    workout = WorkoutBuilder().build(decision, planned)

    execution = ExecutionEngine().analyze_context(
        ExecutionContext(
            workout=workout,
            activity=activity,
            summary=summary,
            timeline=TimelineBuilder().build(workout),
        )
    )

    print()
    print("=" * 60)
    print("BLOCK EXECUTION")
    print("=" * 60)
    print()

    print(f"Workout score : {execution.execution_score:.1f}%")
    print(f"Completion    : {execution.completion_score:.1f}%")
    print(f"TSS           : {execution.executed_tss:.1f} / "
          f"{execution.planned_tss:.1f}")
    print()

    for block in execution.blocks:

        print(block.name)
        print(f" Planned time : {block.planned_duration}s")
        print(f" Actual time  : {block.executed_duration}s")
        print(f" Completion   : {block.completion_score:.1f}%")
        print(f" Power score  : {score(block.power_score)}")
        print(f" Cadence score: {score(block.cadence_score)}")
        print(f" HR score     : {score(block.heart_rate_score)}")
        print(f" Score        : {block.execution_score:.1f}%")

        for deviation in block.deviations:
            print(" •", deviation)

        print()

    if execution.insights:
        print("Insights")
        print("-" * 60)

        for insight in execution.insights:
            print("•", insight)

    print()


if __name__ == "__main__":
    main()
