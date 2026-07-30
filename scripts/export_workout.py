from dataclasses import replace
from pathlib import Path

from athlete.state_builder import AthleteStateBuilder

from config.settings import ZWIFT_WORKOUTS

from decision.engine import DecisionEngine

from engines.context_builder import ContextBuilder

from health.engine import HealthEngine

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository

from training.factories.activity_factory import ActivityFactory
from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.builder import WorkoutBuilder
from workout.calculator import WorkoutCalculator
from workout.export.zwo_exporter import ZwoExporter


def main():

    history = HealthRepository().load_daily()

    context = ContextBuilder().build(history)

    health = HealthEngine().analyze(context)

    recovery = RecoveryEngine().analyze(context)

    performance = PerformanceEngine().analyze()

    activities = Path(
        "/Users/marsm0wa/Documents/Zwift/Activities"
    )

    fit_file = sorted(
        activities.glob("*.fit")
    )[-1]

    parsed_activity = FitParser().parse(
        str(fit_file)
    )

    activity = ActivityFactory().create(parsed_activity)

    workout_summary = WorkoutAnalyzer().analyze(
        activity
    )

    athlete = AthleteStateBuilder().build(

        health=health,

        context=context,

        recovery=recovery,

        performance=performance,

        workout=workout_summary,

    )

    decision = DecisionEngine().decide(
        athlete
    )

    legacy_decision = replace(
        decision.decision,
        recommendation=decision.decision.recommendation.name,
    )

    workout = WorkoutBuilder().build(
        legacy_decision
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
