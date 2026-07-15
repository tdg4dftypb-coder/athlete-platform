from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RawRecord:

    timestamp: datetime

    power: Optional[int]

    heart_rate: Optional[int]

    cadence: Optional[int]

    speed: Optional[float]


@dataclass
class RawActivity:

    start: datetime

    end: datetime

    sport: str

    distance: float

    calories: int

    records: list[RawRecord]