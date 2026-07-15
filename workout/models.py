from dataclasses import dataclass

from workout.blocks import WorkoutBlock


@dataclass
class Workout:

    #
    # Identity
    #

    name: str

    goal: str

    description: str

    #
    # Targets
    #

    duration: int

    target_tss: float

    target_if: float

    #
    # Structure
    #

    blocks: list[WorkoutBlock]