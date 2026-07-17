from dataclasses import dataclass


@dataclass
class ExecutionState:

    planned_duration: int

    executed_duration: int

    duration_score: float

    planned_tss: float

    executed_tss: float

    tss_score: float

    overall_score: float

    completed: bool

    reasons: list[str]