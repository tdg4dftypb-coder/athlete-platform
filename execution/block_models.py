from dataclasses import dataclass


@dataclass
class BlockExecution:

    name: str

    planned_start: int

    planned_end: int

    actual_start: int

    actual_end: int

    planned_power_from: float

    planned_power_to: float

    actual_power: float

    planned_cadence_from: int

    planned_cadence_to: int

    actual_cadence: float

    completion: float

    power_score: float

    cadence_score: float

    execution_score: float

    comment: str