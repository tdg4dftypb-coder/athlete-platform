from pathlib import Path

from athlete.state_builder import AthleteStateBuilder

from config.settings import ZWIFT_WORKOUTS

from decision.engine import DecisionEngine

from engines.context_builder import ContextBuilder

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository

from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.builder import WorkoutBuilder
from workout.calculator import WorkoutCalculator
from workout.export.zwo_exporter import ZwoExporter


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

    metrics = WorkoutCalculator().calculate(
        workout
    )

    file = ZwoExporter().export(

        workout,

        ZWIFT_WORKOUTS,

    )

    print()

    print("Workout exported")

    print()

    print(file)

    print()

    print("Duration :", metrics.duration, "min")

    print("IF       :", round(metrics.expected_if, 2))

    print("TSS      :", round(metrics.expected_tss, 1))

    print()
    

if __name__ == "__main__":
    main()