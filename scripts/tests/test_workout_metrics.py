from pathlib import Path

from athlete.state_builder import AthleteStateBuilder

from decision.engine import DecisionEngine

from engines.context_builder import ContextBuilder

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository

from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.builder import WorkoutBuilder
from workout.calculator import WorkoutCalculator
from workout.validator import WorkoutValidator


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

    workout_summary = WorkoutAnalyzer().analyze(
        activity
    )

    athlete = AthleteStateBuilder().build(

        health=health,

        recovery=recovery,

        performance=performance,

        workout=workout_summary,

    )

    decision = DecisionEngine().decide(
        athlete
    )

    workout = WorkoutBuilder().build(
        decision
    )

    errors = WorkoutValidator().validate(
        workout
    )

    if errors:

        print()

        print("Validation errors")

        for error in errors:

            print("-", error)

        return

    metrics = WorkoutCalculator().calculate(
        workout
    )

    print()

    print("=" * 60)

    print("WORKOUT METRICS")

    print("=" * 60)

    print()

    print("Duration      :", metrics.duration, "min")

    print("Expected IF   :", round(metrics.expected_if, 2))

    print("Expected NP   :", round(metrics.expected_np))

    print("Expected TSS  :", round(metrics.expected_tss, 1))

    print("Calories      :", metrics.estimated_calories)

    print()

    print("Zones")

    print(" Z1 :", round(metrics.z1 / 60), "min")

    print(" Z2 :", round(metrics.z2 / 60), "min")

    print(" Z3 :", round(metrics.z3 / 60), "min")

    print(" Z4 :", round(metrics.z4 / 60), "min")

    print(" Z5 :", round(metrics.z5 / 60), "min")

    print(" Z6 :", round(metrics.z6 / 60), "min")

    print(" Z7 :", round(metrics.z7 / 60), "min")

    print()


if __name__ == "__main__":
    main()