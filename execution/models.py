from dataclasses import dataclass


@dataclass
class WorkoutExecution:

    execution_score: float

    power_score: float

    cadence_score: float

    hr_score: float

    completion: float

    comment: str