"""Performance Lab — domain models.

Frozen dataclasses representing performance testing concepts.
No infrastructure dependencies — only stdlib: dataclasses, datetime, enum.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────


class PerformanceTestType(Enum):
    LACTATE_STEP_TEST = "lactate_step_test"
    CARDIOPULMONARY_EXERCISE_TEST = "cardiopulmonary_exercise_test"
    FTP_TEST = "ftp_test"
    FIELD_TEST = "field_test"


class PerformanceTestStatus(Enum):
    PLANNED = "planned"
    COMPLETED = "completed"
    PARTIAL = "partial"
    INVALID = "invalid"


class ExerciseModality(Enum):
    CYCLING = "cycling"
    RUNNING = "running"
    ROWING = "rowing"
    OTHER = "other"


class StageCompletionStatus(Enum):
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    SKIPPED = "skipped"


# ── PerformanceStage ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PerformanceStage:
    """One step in a graded exercise test protocol."""

    stage_number: int
    completion_status: StageCompletionStatus

    # Optional physiological measurements
    duration_seconds: int | None = None
    power_watts: float | None = None
    speed_kph: float | None = None
    heart_rate_bpm: int | None = None
    lactate_mmol_l: float | None = None
    cadence_rpm: float | None = None
    perceived_exertion: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.stage_number < 1:
            raise ValueError(
                f"stage_number must be >= 1, got {self.stage_number}"
            )
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError(
                f"duration_seconds must be >= 0, got {self.duration_seconds}"
            )
        if self.power_watts is not None and self.power_watts < 0:
            raise ValueError(
                f"power_watts must be >= 0, got {self.power_watts}"
            )
        if self.speed_kph is not None and self.speed_kph < 0:
            raise ValueError(
                f"speed_kph must be >= 0, got {self.speed_kph}"
            )
        if self.heart_rate_bpm is not None and self.heart_rate_bpm <= 0:
            raise ValueError(
                f"heart_rate_bpm must be > 0, got {self.heart_rate_bpm}"
            )
        if self.lactate_mmol_l is not None and self.lactate_mmol_l < 0:
            raise ValueError(
                f"lactate_mmol_l must be >= 0, got {self.lactate_mmol_l}"
            )
        if self.cadence_rpm is not None and self.cadence_rpm < 0:
            raise ValueError(
                f"cadence_rpm must be >= 0, got {self.cadence_rpm}"
            )
        if self.perceived_exertion is not None and not (
            0.0 <= self.perceived_exertion <= 10.0
        ):
            raise ValueError(
                f"perceived_exertion must be in [0, 10], got {self.perceived_exertion}"
            )


# ── PerformanceTestSession ────────────────────────────────────────────────────


@dataclass(frozen=True)
class PerformanceTestSession:
    """A single graded exercise test session."""

    test_id: str
    performed_at: datetime
    test_type: PerformanceTestType
    status: PerformanceTestStatus
    modality: ExerciseModality
    stages: tuple[PerformanceStage, ...]

    # Optional context
    protocol_name: str | None = None
    body_mass_kg: float | None = None
    ambient_temperature_c: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.test_id:
            raise ValueError("test_id must not be empty")
        if not isinstance(self.stages, tuple):
            raise TypeError(
                f"stages must be a tuple, got {type(self.stages).__name__}"
            )
        if self.body_mass_kg is not None and self.body_mass_kg <= 0:
            raise ValueError(
                f"body_mass_kg must be > 0, got {self.body_mass_kg}"
            )
        _validate_stage_ordering(self.stages)


def _validate_stage_ordering(stages: tuple[PerformanceStage, ...]) -> None:
    """Enforce unique stage_numbers in strictly ascending order."""
    numbers = [s.stage_number for s in stages]
    if len(numbers) != len(set(numbers)):
        raise ValueError(
            f"stage_number values must be unique, got duplicates: {numbers}"
        )
    if numbers != sorted(numbers):
        raise ValueError(
            f"stages must be ordered by ascending stage_number, got: {numbers}"
        )


# ── PerformanceThreshold ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class PerformanceThreshold:
    """A physiological threshold identified from test data.

    Calculation is not performed at this layer.
    This model is a stable carrier for threshold results produced by future
    analysis engines (Lactate Curve Engine, Threshold Analysis).
    """

    name: str

    power_watts: float | None = None
    speed_kph: float | None = None
    heart_rate_bpm: int | None = None
    lactate_mmol_l: float | None = None
    confidence: float | None = None
    method: str | None = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
        if self.power_watts is not None and self.power_watts < 0:
            raise ValueError(
                f"power_watts must be >= 0, got {self.power_watts}"
            )
        if self.speed_kph is not None and self.speed_kph < 0:
            raise ValueError(
                f"speed_kph must be >= 0, got {self.speed_kph}"
            )
        if self.heart_rate_bpm is not None and self.heart_rate_bpm <= 0:
            raise ValueError(
                f"heart_rate_bpm must be > 0, got {self.heart_rate_bpm}"
            )
        if self.lactate_mmol_l is not None and self.lactate_mmol_l < 0:
            raise ValueError(
                f"lactate_mmol_l must be >= 0, got {self.lactate_mmol_l}"
            )


# ── PerformanceAssessment ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class PerformanceAssessment:
    """Aggregate of a test session and its analysis results.

    Analysis fields (lt1, lt2, vo2max, fatmax) are populated by future
    engine layers — they are intentionally None at this stage.
    """

    session: PerformanceTestSession

    lt1: PerformanceThreshold | None = None
    lt2: PerformanceThreshold | None = None
    vo2max_ml_kg_min: float | None = None
    fatmax_power_watts: float | None = None
    summary: str | None = None
