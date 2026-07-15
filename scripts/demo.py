from datetime import date, timedelta

from analyzers.readiness.analyzer import ReadinessAnalyzer
from coach.morning_briefing import MorningBriefingPrinter
from core.models import HealthDaily
from core.results import MorningBriefing
from engines.context_builder import ContextBuilder


def main():

    history = [

        HealthDaily(
            date=date.today() - timedelta(days=6),
            hrv=70,
            resting_hr=46,
            sleep_duration=470
        ),

        HealthDaily(
            date=date.today() - timedelta(days=5),
            hrv=71,
            resting_hr=46,
            sleep_duration=460
        ),

        HealthDaily(
            date=date.today() - timedelta(days=4),
            hrv=69,
            resting_hr=47,
            sleep_duration=455
        ),

        HealthDaily(
            date=date.today() - timedelta(days=3),
            hrv=72,
            resting_hr=46,
            sleep_duration=480
        ),

        HealthDaily(
            date=date.today() - timedelta(days=2),
            hrv=70,
            resting_hr=47,
            sleep_duration=470
        ),

        HealthDaily(
            date=date.today() - timedelta(days=1),
            hrv=71,
            resting_hr=46,
            sleep_duration=465
        ),

        HealthDaily(
            date=date.today(),
            hrv=63,
            resting_hr=51,
            sleep_duration=390
        )

    ]

    context = ContextBuilder().build(history)

    readiness = ReadinessAnalyzer().analyze(context)

    briefing = MorningBriefing(
        readiness=readiness,
        recommendation=readiness.recommendation,
        alerts=[]
    )

    MorningBriefingPrinter().print(briefing)


if __name__ == "__main__":
    main()