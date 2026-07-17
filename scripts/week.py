from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planning.engine import PlanningEngine


def format_duration(minutes: int) -> str:

    if minutes == 0:
        return "-"

    hours = minutes // 60
    mins = minutes % 60

    if hours == 0:
        return f"{mins} min"

    return f"{hours} h {mins:02d} min"


def main():

    plan = PlanningEngine().build()

    total_minutes = 0
    total_tss = 0

    print()
    print("=" * 72)
    print("THIS WEEK")
    print("=" * 72)
    print()

    for day in plan.days:

        total_minutes += day.duration
        total_tss += day.target_tss

        print(
            f"{day.day:<4}"
            f"{day.workout:<15}"
            f"{format_duration(day.duration):<10}"
            f"{day.target_tss:>5.0f} TSS"
        )

    print()
    print("-" * 72)

    print(f"Weekly Time : {format_duration(total_minutes)}")
    print(f"Weekly TSS  : {total_tss:.0f}")

    print()
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()