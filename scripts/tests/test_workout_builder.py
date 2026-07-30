from pathlib import Path

from athlete.state_builder import AthleteStateBuilder
from decision.engine import DecisionEngine
from engines.context_builder import ContextBuilder
from performance.engine import PerformanceEngine
from recovery.engine import RecoveryEngine
from repositories.health_repository import HealthRepository

from training.factories.activity_factory import ActivityFactory
from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.builder import WorkoutBuilder


def main():

    #
    # Health
    #

    history = HealthRepository().load_daily()

    health = ContextBuilder().build(history)

    recovery = RecoveryEngine().analyze(health)

    #
    # Performance
    #

    performance = PerformanceEngine().analyze()

    #
    # Last workout
    #

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

    #
    # Athlete
    #

    athlete = AthleteStateBuilder().build(

        health=health,

        recovery=recovery,

        performance=performance,

        workout=workout_summary,

    )

    #
    # Decision
    #

    decision = DecisionEngine().decide(
        athlete
    )

    #
    # Workout
    #

    workout = WorkoutBuilder().build(
        decision
    )

    print()
    print("=" * 60)
    print("WORKOUT")
    print("=" * 60)
    print()

    print("Name       :", workout.name)
    print("Goal       :", workout.goal)
    print("Duration   :", workout.duration, "min")
    print("Target TSS :", workout.target_tss)
    print("Target IF  :", workout.target_if)

    #
    # REST DAY
    #

    if not workout.blocks:

        print()
        print("Rest day.")
        return

    print()
    print("Blocks")
    print()

    total = 0

    for i, block in enumerate(workout.blocks, start=1):

        total += block.duration

        print(f"{i}. {block.name}")

        print(
            f"   Time     : {block.duration // 60} min"
        )

        if block.power_from == block.power_to:

            print(
                f"   Power    : {int(block.power_from * 100)} % FTP"
            )

        else:

            print(
                f"   Power    : "
                f"{int(block.power_from * 100)} - "
                f"{int(block.power_to * 100)} % FTP"
            )

        print(
            f"   Cadence  : "
            f"{block.cadence_from}-{block.cadence_to} rpm"
        )

        if block.repeat > 1:

            print(
                f"   Repeat   : {block.repeat}x"
            )

        print(
            f"   Desc     : {block.description}"
        )

        print()

    print(
        "Total block time:",
        round(total / 60),
        "min"
    )

    print()


if __name__ == "__main__":
    main()
