from pathlib import Path

from athlete.state_builder import AthleteStateBuilder

from decision.engine import DecisionEngine

from engines.context_builder import ContextBuilder

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository

from timeline.builder import TimelineBuilder

from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.builder import WorkoutBuilder


def format_time(seconds: int):

    minutes = seconds // 60

    sec = seconds % 60

    return f"{minutes:02}:{sec:02}"


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

    timeline = TimelineBuilder().build(
        workout
    )

    print()

    print("=" * 60)

    print("WORKOUT TIMELINE")

    print("=" * 60)

    print()

    for block in timeline.blocks:

        print(

            f"{format_time(block.start)}"

            f" -> "

            f"{format_time(block.end)}"

            f"   "

            f"{block.name}"

        )

        print(

            f"   Power   : "

            f"{int(block.power_from*100)}"

            f"-"

            f"{int(block.power_to*100)} % FTP"

        )

        print(

            f"   Cadence : "

            f"{block.cadence_from}"

            f"-"

            f"{block.cadence_to}"

        )

        if block.repeat > 1:

            print(

                f"   Repeat  : "

                f"{block.repeat}"

            )

        print()

    print(

        "Total duration :",

        round(timeline.total_duration / 60),

        "min"

    )

    print()


if __name__ == "__main__":
    main()