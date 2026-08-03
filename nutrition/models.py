from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class NutritionDataStatus(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class NutritionInput:
    valid_for_date: date
    as_of: datetime
    body_mass_kg: float | None = None
    body_mass_observed_at: datetime | None = None
    resting_energy_kcal: float | None = None
    active_energy_kcal: float | None = None
    energy_observed_for_date: date | None = None
    recovery_score: float | None = None
    planned_sport: str | None = None
    planned_workout_type: str | None = None
    planned_duration_min: int | None = None
    planned_target_tss: float | None = None
    planned_intensity: str | None = None
    workout_start: datetime | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnergyRequirement:
    estimated_daily_requirement_kcal: float | None = None
    observed_daily_expenditure_kcal: float | None = None
    resting_energy_kcal: float | None = None
    active_energy_kcal: float | None = None


@dataclass(frozen=True)
class MacroTargets:
    carbohydrate_g: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbohydrate_g_per_kg: float | None = None
    protein_g_per_kg: float | None = None
    fat_g_per_kg: float | None = None


@dataclass(frozen=True)
class FuelingPlan:
    pre_workout_carbohydrate_g: float | None = None
    during_workout_carbohydrate_g_per_hour: float | None = None
    post_workout_carbohydrate_g: float | None = None
    post_workout_protein_g: float | None = None
    pre_workout_window_min: int | None = None
    post_workout_window_min: int | None = None


@dataclass(frozen=True)
class HydrationTarget:
    daily_ml: float | None = None
    daily_ml_per_kg: float | None = None
    pre_workout_ml: float | None = None
    during_workout_ml_per_hour: float | None = None
    post_workout_ml: float | None = None


@dataclass(frozen=True)
class NutritionAssessment:
    energy_requirement: EnergyRequirement
    macro_targets: MacroTargets
    fueling_plan: FuelingPlan
    hydration_target: HydrationTarget
    data_status: NutritionDataStatus
    confidence: float
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    valid_for_date: date
    as_of: datetime
