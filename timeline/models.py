from dataclasses import dataclass


@dataclass
class TimelineBlock:

    index: int

    name: str

    start: int

    end: int

    duration: int

    power_from: float

    power_to: float

    cadence_from: int

    cadence_to: int

    repeat: int

    description: str


@dataclass
class WorkoutTimeline:

    blocks: list[TimelineBlock]

    total_duration: int