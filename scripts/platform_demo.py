from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planner.engine import PlannerEngine

from workout.builders.workout_builder import WorkoutBuilder

from simulator.engine import SimulatorEngine
from timeline.builder import TimelineBuilder

from decision.models import DecisionState
from decision.sports import Sport


def format_time(seconds: int) -> str:

    minutes = seconds // 60
    secs = seconds % 60

    return f"{minutes:02d}:{secs:02d}"


def main():

    decision = DecisionState(

        sport=Sport.CYCLING,

        recommendation="TEMPO",

        duration=90,

        target_tss=70,

        intensity="Z3",

        reasons=[],

        priority=100,

        confidence=100,

        source_rules=[],

    )

    #
    # Planner
    #

    planned = PlannerEngine().build(

        decision

    )

    #
    # Workout
    #

    workout = WorkoutBuilder().build(

        decision,

        planned,

    )

    #
    # Simulation
    #

    simulation = SimulatorEngine().simulate(

        workout

    )

    #
    # Timeline
    #

    timeline = TimelineBuilder().build(

        workout

    )

    print()
    print("=" * 72)
    print("ATHLETE PLATFORM PIPELINE")
    print("=" * 72)
    print()

    print("Workout")
    print("-" * 72)

    print(workout.name)

    print(f"Goal       : {workout.goal}")
    print(f"Duration   : {workout.duration} min")
    print(f"Target TSS : {workout.target_tss:.1f}")

    print()

    print("Simulation")
    print("-" * 72)

    print(f"Average Power : {simulation.average_power:.0f} W")
    print(f"NP            : {simulation.normalized_power:.0f} W")
    print(f"IF            : {simulation.intensity_factor:.2f}")
    print(f"TSS           : {simulation.tss:.1f}")

    print()

    print("Timeline")
    print("-" * 72)

    for block in timeline.blocks:

        print(
            f"{format_time(block.start)}  "
            f"{format_time(block.end)}   "
            f"{block.name}"
        )

    print()
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()