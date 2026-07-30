from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkoutPrescription:

    duration: int

    target_tss: float

    interval_structure: str

    warmup_minutes: int = 10

    cooldown_minutes: int = 10