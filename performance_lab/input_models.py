"""Performance Lab — input models.

Frozen dataclasses carrying raw user-supplied data for the builder.
Distinct from domain models: they do not enforce domain invariants beyond
structural requirements (tuple types, no mutable collections).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from performance_lab.domain import (
    ExerciseModality,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)


@dataclass(frozen=True)
class PerformanceStageInput:
    """Raw data for one stage of a graded exercise test.

    Field values are validated by the domain model on build.
    No implicit type coercion is performed here.
    """

    stage_number: int
    completion_status: StageCompletionStatus

    duration_seconds: int | None = None
    power_watts: float | None = None
    speed_kph: float | None = None
    heart_rate_bpm: int | None = None
    lactate_mmol_l: float | None = None
    cadence_rpm: float | None = None
    perceived_exertion: float | None = None
    notes: str | None = None


@dataclass(frozen=True)
class PerformanceTestSessionInput:
    """Raw data for a full performance test session.

    Stages must be supplied as a tuple. Ordering and uniqueness are
    enforced by the domain model during build, not here.
    """

    test_id: str
    performed_at: datetime
    test_type: PerformanceTestType
    status: PerformanceTestStatus
    modality: ExerciseModality
    stages: tuple[PerformanceStageInput, ...]

    protocol_name: str | None = None
    body_mass_kg: float | None = None
    ambient_temperature_c: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stages, tuple):
            raise TypeError(
                f"stages must be a tuple, got {type(self.stages).__name__}"
            )
