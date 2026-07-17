from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planner.dsl.compiler import DSLCompiler
from planner.dsl.parser import DSLParser
from planner.converters.workout_converter import WorkoutConverter
from timeline.builder import TimelineBuilder


def format_time(seconds: int) -> str:

    minutes = seconds // 60
    secs = seconds % 60

    return f"{minutes:02d}:{secs:02d}"


def main():

    planned = DSLCompiler().compile(
        DSLParser().tempo()
    )

    workout = WorkoutConverter().convert(planned)

    timeline = TimelineBuilder().build(workout)

    print()
    print("=" * 72)
    print(workout.name)
    print("=" * 72)
    print()

    for block in timeline.blocks:

        print(

            f"{format_time(block.start)}"

            f"  "

            f"{format_time(block.end)}"

            f"   "

            f"{block.name:<12}"

            f"{block.power_from:.2f}"

            "-"

            f"{block.power_to:.2f}"

        )

    print()
    print("-" * 72)

    print(

        "Total:",

        format_time(

            timeline.total_duration

        )

    )

    print()


if __name__ == "__main__":
    main()