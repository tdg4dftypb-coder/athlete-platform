from dataclasses import dataclass

from decision.sports import Sport


@dataclass(frozen=True)
class WorkoutTemplate:

    sport: Sport

    recommendation: str

    duration: int

    target_tss: float

    intensity: str