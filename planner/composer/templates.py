from dataclasses import dataclass


@dataclass(frozen=True)
class WorkoutTemplate:

    warmup: int

    cooldown: int

    interval_duration: int

    recovery_duration: int

    repeats: int

    power: float

    recovery_power: float