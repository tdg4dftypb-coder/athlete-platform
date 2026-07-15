from pathlib import Path

from athlete.state_builder import AthleteStateBuilder

from decision.engine import DecisionEngine

from engines.context_builder import ContextBuilder

from execution.analyzer import ExecutionAnalyzer

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository

from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.builder import WorkoutBuilder


def main():

    history = HealthRepository().load_daily()

    health = ContextBuilder().build(history)

    recovery = RecoveryEngine().analyze(health)

    performance = PerformanceEngine().analyze()

    activities = Path(
        "/Users/marsm0wa/Documents/Zwift/Activities"
    )

    fit_file = sorted(
        activities.glob("*.fit")
    )[-1]

    activity = FitParser().parse(
        str(fit_file)
    )

    summary = WorkoutAnalyzer().analyze(
        activity
    )

    athlete = AthleteStateBuilder().build(

        health=health,

        recovery=recovery,

        performance=performance,

        workout=summary,

    )

    decision = DecisionEngine().decide(
        athlete
    )

    workout = WorkoutBuilder().build(
        decision
    )

    execution = ExecutionAnalyzer().analyze(

        workout,

        summary,

    )

    print()

    print("=" * 60)

    print("WORKOUT EXECUTION")

    print("=" * 60)

    print()

    print("Execution :", execution.execution_score)

    print("Power     :", execution.power_score)

    print("Cadence   :", execution.cadence_score)

    print("HR        :", execution.hr_score)

    print("Completion:", execution.completion)

    print()

    print(execution.comment)

    print()


if __name__ == "__main__":
    main()