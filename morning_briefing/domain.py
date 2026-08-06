from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Union, Tuple


class MorningStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


class MorningPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class MorningMetric:
    title: str
    value: Optional[Union[int, float, str]]
    unit: Optional[str]
    status: str


@dataclass(frozen=True)
class MorningRecommendation:
    title: str
    description: str
    priority: MorningPriority


@dataclass(frozen=True)
class MorningSection:
    title: str
    summary: str
    metrics: Tuple[MorningMetric, ...] = ()
    recommendations: Tuple[MorningRecommendation, ...] = ()


@dataclass(frozen=True)
class MorningBriefing:
    generated_at: datetime
    status: MorningStatus
    sections: Tuple[MorningSection, ...] = ()
