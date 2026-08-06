from dataclasses import dataclass
from enum import Enum, auto


class TrendDirection(Enum):
    INCREASING = auto()
    DECREASING = auto()
    STABLE = auto()
    INSUFFICIENT_DATA = auto()


class TrendStrength(Enum):
    NONE = auto()
    WEAK = auto()
    MODERATE = auto()
    STRONG = auto()


class TrendWindow(Enum):
    ALL_TIME = auto()


@dataclass(frozen=True)
class BiomarkerTrend:
    canonical_code: str
    first_value: float | None
    latest_value: float | None
    absolute_change: float | None
    relative_change: float | None
    direction: TrendDirection
    strength: TrendStrength
    window: TrendWindow
    observations: int
