from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ContextDataStatus(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


@dataclass(frozen=True)
class RecoveryDecisionContext:
    status: ContextDataStatus
    recovery_score: float | None = None
    recovery_status: str | None = None
    hrv_status: str | None = None
    resting_heart_rate_status: str | None = None
    sleep_status: str | None = None
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ContextDataStatus):
            raise ValueError("status must be a ContextDataStatus")
        if self.recovery_score is not None:
            if not (0.0 <= self.recovery_score <= 100.0):
                raise ValueError("recovery_score must be between 0.0 and 100.0")


@dataclass(frozen=True)
class TrainingDecisionContext:
    status: ContextDataStatus
    planned_session_type: str | None = None
    planned_duration_minutes: int | None = None
    planned_intensity: str | None = None
    recent_training_load: float | None = None
    fatigue_status: str | None = None
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ContextDataStatus):
            raise ValueError("status must be a ContextDataStatus")
        if self.planned_duration_minutes is not None:
            if self.planned_duration_minutes < 0:
                raise ValueError("planned_duration_minutes must be >= 0")
        if self.recent_training_load is not None:
            if self.recent_training_load < 0.0:
                raise ValueError("recent_training_load must be >= 0")


@dataclass(frozen=True)
class BiomarkerDecisionSignal:
    canonical_code: str
    interpretation: str
    confidence: str
    summary: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_code, str) or not self.canonical_code.strip():
            raise ValueError("canonical_code must be non-empty string")
        if not isinstance(self.interpretation, str) or not self.interpretation.strip():
            raise ValueError("interpretation must be non-empty string")
        if not isinstance(self.confidence, str) or not self.confidence.strip():
            raise ValueError("confidence must be non-empty string")


@dataclass(frozen=True)
class BiomarkerDecisionContext:
    status: ContextDataStatus
    attention_count: int
    critical_count: int
    signals: tuple[BiomarkerDecisionSignal, ...] = ()
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ContextDataStatus):
            raise ValueError("status must be a ContextDataStatus")
        if self.attention_count < 0:
            raise ValueError("attention_count must be >= 0")
        if self.critical_count < 0:
            raise ValueError("critical_count must be >= 0")
        if self.critical_count > self.attention_count:
            raise ValueError("critical_count must be <= attention_count")
        if not isinstance(self.signals, tuple):
            raise TypeError("signals must be a tuple")

        seen_codes: set[str] = set()
        for sig in self.signals:
            if not isinstance(sig, BiomarkerDecisionSignal):
                raise TypeError("signals items must be BiomarkerDecisionSignal")
            if sig.canonical_code in seen_codes:
                raise ValueError(f"Duplicate canonical_code in signals: {sig.canonical_code}")
            seen_codes.add(sig.canonical_code)


@dataclass(frozen=True)
class PerformanceThresholdSnapshot:
    name: str
    status: str
    power_watts: float | None = None
    speed_kph: float | None = None
    heart_rate_bpm: int | None = None
    lactate_mmol_l: float | None = None
    confidence: float | None = None
    method: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be non-empty string")
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status must be non-empty string")
        if self.power_watts is not None and self.power_watts < 0.0:
            raise ValueError("power_watts must be >= 0")
        if self.speed_kph is not None and self.speed_kph < 0.0:
            raise ValueError("speed_kph must be >= 0")
        if self.heart_rate_bpm is not None and self.heart_rate_bpm <= 0:
            raise ValueError("heart_rate_bpm must be > 0")
        if self.lactate_mmol_l is not None and self.lactate_mmol_l < 0.0:
            raise ValueError("lactate_mmol_l must be >= 0")
        if self.confidence is not None:
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class PerformanceDecisionContext:
    status: ContextDataStatus
    latest_test_id: str | None = None
    latest_test_type: str | None = None
    performed_at: datetime | None = None
    lt1: PerformanceThresholdSnapshot | None = None
    lt2: PerformanceThresholdSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ContextDataStatus):
            raise ValueError("status must be a ContextDataStatus")

        if self.latest_test_id is None:
            if self.latest_test_type is not None:
                raise ValueError("latest_test_type must be None when latest_test_id is None")
            if self.performed_at is not None:
                raise ValueError("performed_at must be None when latest_test_id is None")
            if self.lt1 is not None:
                raise ValueError("lt1 must be None when latest_test_id is None")
            if self.lt2 is not None:
                raise ValueError("lt2 must be None when latest_test_id is None")


@dataclass(frozen=True)
class AthleteDecisionContext:
    generated_at: datetime
    recovery: RecoveryDecisionContext
    training: TrainingDecisionContext
    biomarkers: BiomarkerDecisionContext
    performance: PerformanceDecisionContext

    def __post_init__(self) -> None:
        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be a datetime")
        if not isinstance(self.recovery, RecoveryDecisionContext):
            raise TypeError("recovery must be RecoveryDecisionContext")
        if not isinstance(self.training, TrainingDecisionContext):
            raise TypeError("training must be TrainingDecisionContext")
        if not isinstance(self.biomarkers, BiomarkerDecisionContext):
            raise TypeError("biomarkers must be BiomarkerDecisionContext")
        if not isinstance(self.performance, PerformanceDecisionContext):
            raise TypeError("performance must be PerformanceDecisionContext")
