from dataclasses import dataclass


@dataclass
class BlockExecution:

    name: str

    start: int

    end: int

    duration: int

    completion: float

    target_power_from: float

    target_power_to: float

    average_power: float

    power_score: float

    target_cadence_from: int

    target_cadence_to: int

    average_cadence: float

    cadence_score: float

    average_hr: float

    hr_score: float

    execution_score: float

    comment: str