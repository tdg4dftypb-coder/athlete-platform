from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionState:
    recovery: float
    fatigue: float

    sleep_score: float
    hrv_score: float

    resting_hr: int

    available_minutes: int