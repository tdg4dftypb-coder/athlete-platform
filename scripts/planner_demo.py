from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planner.dsl.compiler import DSLCompiler
from planner.dsl.parser import DSLParser


def main():

    workout = DSLParser().tempo()

    planned = DSLCompiler().compile(workout)

    print()
    print("=" * 72)
    print(planned.name)
    print("=" * 72)

    total = 0

    for block in planned.blocks:

        minutes = block.duration // 60

        total += minutes

        print(
            f"{block.name:<12}"
            f"{minutes:>3} min   "
            f"{block.power_from:.2f}"
            f"-"
            f"{block.power_to:.2f}"
        )

    print()
    print(f"Total: {total} min")
    print()


if __name__ == "__main__":
    main()