from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ParsedActivityRecord:
    """Transport record extracted from an activity file."""

    timestamp: Optional[datetime]

    power: Optional[int]

    heart_rate: Optional[int]

    cadence: Optional[int]

    speed: Optional[float]


@dataclass(frozen=True)
class ParsedActivity:
    """Transport model shared by activity-file parsers."""

    start: Optional[datetime]

    end: Optional[datetime]

    sport: Optional[str]

    distance: float

    calories: int

    records: list[ParsedActivityRecord]
