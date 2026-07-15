from pathlib import Path

from athlete.state_builder import AthleteStateBuilder

from decision.engine import DecisionEngine

from engines.context_builder import ContextBuilder

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository

from timeline.builder import TimelineBuilder

from training.activity_builder import ActivityBuilder
from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer

from workout.builder import WorkoutBuilder

from execution.workout_execution import WorkoutExecution


def percent(value):

    return f"{round(value * 100)} %"


def time(seconds):

    minutes = seconds // 60

    sec = seconds % 60

    return f"{minutes:02}:{sec:02}"


def main():

    #
    # Health
    #

    history = HealthRepository().load_daily()

    health = ContextBuilder().build(history)

    recovery = RecoveryEngine().analyze(health)

    performance = PerformanceEngine().analyze()

    #
    # FIT
    #

    activities = Path(
        "/Users/marsm0wa/Documents/Zwift/Activities"
    )

    fit = sorted(
        activities.glob("*.fit")
    )[-1]

    raw = FitParser().parse(
        str(fit)
    )

    activity = ActivityBuilder().build(
        raw
    )

    summary = WorkoutAnalyzer().analyze(
        raw
    )

    #
    # Athlete
    #

    athlete = AthleteStateBuilder().build(

        health=health,

        recovery=recovery,

        performance=performance,

        workout=summary,

    )

    #
    # Decision
    #

    decision = DecisionEngine().decide(
        athlete
    )

    #
    # Planned workout
    #

    workout = WorkoutBuilder().build(
        decision
    )

    timeline = TimelineBuilder().build(
        workout
    )

    #
    # Execution
    #

    execution = WorkoutExecution().analyze(

        workout,

        activity,

    )

    #
    # Report
    #

    print()

    print("=" * 60)

    print("BLOCK EXECUTION")

    print("=" * 60)

    print()

    total = 0

    for planned, block in zip(

        timeline.blocks,

        execution,

    ):

        total += block.execution_score

        print(

            f"{planned.name}"

        )

        print(

            f" Time       : "

            f"{time(planned.start)}"

            f" -> "

            f"{time(planned.end)}"

        )

        print(

            f" Target Pow : "

            f"{percent(planned.power_from)}"

            f" - "

            f"{percent(planned.power_to)}"

        )

        print(

            f" Avg Power  : "

            f"{round(block.average_power)} W"

        )

        print(

            f" PowerScore : "

            f"{round(block.power_score,1)}"

        )

        print(

            f" Avg Cad    : "

            f"{round(block.average_cadence)}"

        )

        print(

            f" Cad Score  : "

            f"{round(block.cadence_score,1)}"

        )

        print(

            f" Avg HR     : "

            f"{round(block.average_hr)}"

        )

        print(

            f" Completion : "

            f"{round(block.completion,1)} %"

        )

        print(

            f" Score      : "

            f"{round(block.execution_score,1)}"

        )

        print()

    print("=" * 60)

    print()

    print(

        "Workout Execution :",

        round(

            total / len(execution),

            1,

        )

    )

    print()