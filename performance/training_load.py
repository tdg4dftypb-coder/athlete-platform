from dataclasses import dataclass


@dataclass
class TrainingLoad:

    total_tss: float

    average_tss: float

    workouts: int

    average_daily_tss: float

    period_days: int