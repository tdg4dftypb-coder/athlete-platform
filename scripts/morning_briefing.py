from pathlib import Path

from athlete.state_builder import AthleteStateBuilder

from briefing.builder import MorningBriefingBuilder
from briefing.formatter import ConsoleFormatter
from briefing.html_formatter import HtmlFormatter

from coach.engine import CoachEngine

from decision.engine import DecisionEngine

from engines.context_builder import ContextBuilder

from performance.engine import PerformanceEngine

from recovery.engine import RecoveryEngine

from repositories.health_repository import HealthRepository

from training.parsers.fit_parser import FitParser
from training.analysis.workout_analyzer import WorkoutAnalyzer


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

    activity = FitParser().parse(
        str(fit_file)
    )

    workout = WorkoutAnalyzer().analyze(
        activity
    )

    #
    # Athlete
    #

    athlete = AthleteStateBuilder().build(

        health=health,

        recovery=recovery,

        performance=performance,

        workout=workout,

    )

    #
    # Decision
    #

    decision = DecisionEngine().decide(
        athlete
    )

    #
    # Coach
    #

    coach = CoachEngine().recommend(

        athlete,

        decision,

    )

    #
    # Morning Briefing
    #

    briefing = MorningBriefingBuilder().build(

        athlete,

        decision,

        coach,

    )

    #
    # Output
    #

    ConsoleFormatter().print(
        briefing
    )

    HtmlFormatter().save(
        briefing
    )

    print()

    print("Performance")

    print(" ATL :", round(performance.atl, 1))

    print(" CTL :", round(performance.ctl, 1))

    print(" TSB :", round(performance.tsb, 1))

    print()

    print("Decision")

    print(" Recommendation :", decision.recommendation)

    print(" Duration       :", decision.duration)

    print(" Target TSS     :", decision.target_tss)

    print(" Intensity      :", decision.intensity)

    print()

    print("Reasons")

    for reason in decision.reasons:

        print(" -", reason)

    print()


if __name__ == "__main__":
    main()