from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class BodyCompositionDataStatus(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class BodyCompositionObservation:
    observed_for_date: date
    body_mass_kg: float | None = None
    body_fat_percent: float | None = None
    muscle_mass_kg: float | None = None
    body_water_percent: float | None = None
    visceral_fat_rating: float | None = None
    basal_metabolic_rate_kcal: float | None = None
    waist_circumference_cm: float | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class BodyMeasurement:
    value: float
    observed_at: datetime


@dataclass(frozen=True)
class BodyCompositionProfile:
    body_mass: BodyMeasurement | None = None
    body_fat: BodyMeasurement | None = None
    muscle_mass: BodyMeasurement | None = None
    body_water: BodyMeasurement | None = None
    visceral_fat: BodyMeasurement | None = None
    basal_metabolic_rate: BodyMeasurement | None = None
    waist_circumference: BodyMeasurement | None = None


@dataclass(frozen=True)
class BodyMassTrend:
    current: BodyMeasurement
    baseline: BodyMeasurement
    period_days: int
    absolute_change_kg: float
    percentage_change: float


@dataclass(frozen=True)
class BodyCompositionInput:
    observations: tuple[BodyCompositionObservation, ...]
    valid_for_date: date
    as_of: datetime
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class BodyCompositionAssessment:
    """Body Composition result with aggregate completeness metadata.

    ``data_status`` describes completeness of the entire assessment.
    ``confidence`` is a deterministic completeness score, not an estimate of
    accuracy, sensor quality, or clinical certainty.
    """

    profile: BodyCompositionProfile
    body_mass_trend: BodyMassTrend | None
    data_status: BodyCompositionDataStatus
    confidence: float
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    valid_for_date: date
    as_of: datetime
