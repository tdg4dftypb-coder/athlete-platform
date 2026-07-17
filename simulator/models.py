from dataclasses import dataclass


@dataclass
class SimulatedBlock:

    name: str

    duration: int

    average_power: float

    normalized_power: float

    intensity_factor: float

    tss: float


@dataclass
class SimulatedWorkout:

    duration: int

    average_power: float

    normalized_power: float

    intensity_factor: float

    tss: float

    blocks: list[SimulatedBlock]