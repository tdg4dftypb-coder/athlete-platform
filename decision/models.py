from dataclasses import dataclass


@dataclass
class DecisionState:

    recommendation: str

    duration: int

    target_tss: float

    intensity: str

    reasons: list[str]