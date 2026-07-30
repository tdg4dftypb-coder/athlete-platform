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
    print("WORKOUT EXECUTION")
    print("=" * 60)
    print()
    print(f"Execution  : {execution.execution_score:.1f}%")
    print(f"Completion : {execution.completion_score:.1f}%")
    print(f"Duration   : {execution.executed_duration} / "
          f"{execution.planned_duration} min")
    print(f"TSS        : {execution.executed_tss:.1f} / "
          f"{execution.planned_tss:.1f}")
    print(f"Blocks     : {len(execution.blocks)}")
    print(
        "Status     :",
        "COMPLETED" if execution.completed else "NOT COMPLETED",
    )

    if execution.insights:
        print()
        print("Insights")
        print("-" * 60)

        for insight in execution.insights:
            print("•", insight)

    print()


if __name__ == "__main__":
    main()
