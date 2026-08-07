from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RecoveryMetricStatus(str, Enum):
    SUPPORTIVE = "supportive"
    NEUTRAL = "neutral"
    CAUTION = "caution"
    LIMITING = "limiting"
    UNAVAILABLE = "unavailable"


@dataclass
class RecoveryMetric:

    value: Optional[float]

    baseline: Optional[float]

    delta: Optional[float]

    delta_percent: Optional[float]

    score: int

    status: RecoveryMetricStatus = RecoveryMetricStatus.UNAVAILABLE


@dataclass
class RecoveryResult:

    score: int

    status: str

    reasons: list[str]

    hrv: RecoveryMetric

    resting_hr: RecoveryMetric

    sleep: RecoveryMetric