from dataclasses import dataclass
from typing import Optional


@dataclass
class RecoveryMetric:

    value: Optional[float]

    baseline: Optional[float]

    delta: Optional[float]

    delta_percent: Optional[float]

    score: int


@dataclass
class RecoveryResult:

    score: int

    status: str

    reasons: list[str]

    hrv: RecoveryMetric

    resting_hr: RecoveryMetric

    sleep: RecoveryMetric