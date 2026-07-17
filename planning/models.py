from dataclasses import dataclass


@dataclass
class PlannedDay:

    day: str

    workout: str

    duration: int

    target_tss: float


@dataclass
class WeeklyPlan:

    days: list[PlannedDay]