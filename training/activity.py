from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ActivityRecord:

    timestamp: datetime

    elapsed_time: int

    power: Optional[float]

    heart_rate: Optional[int]

    cadence: Optional[float]

    speed: Optional[float]


@dataclass
class Activity:

    start: datetime

    end: datetime

    sport: str

    distance: float

    calories: int

    duration: int

    records: list[ActivityRecord]