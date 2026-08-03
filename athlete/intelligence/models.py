from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AthleteObservationType(Enum):
    HRV_BELOW_BASELINE = "hrv_below_baseline"
    HRV_ABOVE_BASELINE = "hrv_above_baseline"
    SLEEP_DEBT = "sleep_debt"
    EXECUTION_LOW = "execution_low"
    TRAINING_LOAD_HIGH = "training_load_high"
    RECOVERY_GOOD = "recovery_good"


@dataclass(frozen=True)
class AthleteObservation:
    id: str
    type: AthleteObservationType
    value: float
    confidence: float
    observed_at: datetime
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class HealthObservationInput:
    """Prepared health metrics required by the health observation projection."""

    observed_at: datetime
    hrv_delta_percent: float | None
    sleep_duration_minutes: float | None
    sleep_baseline_minutes: float | None
    recovery_score: float | None
    evidence: tuple[str, ...]


class AthleteInsightType(Enum):
    NEED_MORE_RECOVERY = "need_more_recovery"
    RESPONDS_WELL_TO_SST = "responds_well_to_sst"
    LIMIT_VO2_AFTER_CROSSFIT = "limit_vo2_after_crossfit"
    HIGH_TRAINING_COMPLIANCE = "high_training_compliance"
    FATIGUE_ACCUMULATING = "fatigue_accumulating"


@dataclass(frozen=True)
class AthleteInsight:
    id: str
    type: AthleteInsightType
    confidence: float
    evidence: tuple[str, ...]
    as_of: datetime
