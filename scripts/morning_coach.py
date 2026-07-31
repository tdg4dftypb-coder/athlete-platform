from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application import (
    MorningCoachReport,
)
from application.composition import build_morning_coach_use_case
from core.database import Database


def build_report() -> MorningCoachReport:
    """Run the existing deterministic AI Coach workflow for the current day."""

    database = Database()
    try:
        use_case = build_morning_coach_use_case(database)
        return use_case.run().report
    finally:
        database.close()


def render(report: MorningCoachReport) -> None:
    print("=" * 41)
    print("AI COACH")
    print("=" * 41)
    print()
    print("Status:")
    print(report.athlete_assessment.status.value)
    print()
    print("Today's workout:")
    print(report.workout.name)
    print()
    print("Explanation:")
    print(report.explanation.summary)
    print()
    print("Reasons:")
    for reason in report.explanation.reasons:
        print(f"- {reason}")
    print()
    print("=" * 41)


def main() -> None:
    render(build_report())


if __name__ == "__main__":
    main()
