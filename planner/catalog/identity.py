from dataclasses import dataclass

from workout.enums import WorkoutType


@dataclass(
    frozen=True,
    slots=True,
)
class TrainingIdentity:

    id: str

    name: str

    workout_type: WorkoutType

    dsl: WorkoutType

    version: int = 1