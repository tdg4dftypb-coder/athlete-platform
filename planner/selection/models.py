from dataclasses import dataclass

from decision.prescription.models import TrainingObjective


@dataclass(
    slots=True,
    frozen=True,
)
class SelectionContext:

    #
    # Availability
    #

    available_minutes: int

    #
    # Training target
    #

    target_tss: int

    #
    # Requested workout
    #

    workout_type: str | None = None

    #
    # Adaptation objective
    #

    objective: TrainingObjective | None = None

    #
    # Athlete state
    #

    recovery_score: int = 100

    fatigue_score: float = 0.0