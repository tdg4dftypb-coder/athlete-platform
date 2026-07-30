from dataclasses import dataclass


@dataclass
class PlannedBlock:

    name: str

    duration: int

    power_from: float

    power_to: float

    cadence_from: int

    cadence_to: int

    description: str = ""

    repeat: int = 1


@dataclass
class PlannedWorkout:

    name: str

    sport: str

    target_tss: float

    estimated_duration: int

    blocks: list[PlannedBlock]