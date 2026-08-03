from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


DASHBOARD_CONTRACT_VERSION = "1.0"


class DashboardSectionStatus(Enum):
    """Section availability/completeness, never accuracy or reliability."""

    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class DashboardSectionMetadata:
    """Read-side metadata with an optional source completeness score."""

    status: DashboardSectionStatus
    completeness_score: float | None
    limitations: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class DashboardHealthSection:
    metadata: DashboardSectionMetadata
    hrv_ms: float | None
    resting_heart_rate_bpm: float | None
    sleep_minutes: int | None
    steps: int | None
    active_energy_kcal: float | None
    resting_energy_kcal: float | None
    respiratory_rate_per_minute: float | None
    oxygen_saturation_percent: float | None
    wrist_temperature_celsius: float | None


@dataclass(frozen=True)
class DashboardRecoverySection:
    metadata: DashboardSectionMetadata
    recovery_score: int | None
    sleep_score: int | None


@dataclass(frozen=True)
class DashboardPerformanceSection:
    metadata: DashboardSectionMetadata
    weekly_training_load_tss: float | None
    monthly_training_load_tss: float | None
    fatigue_tss_per_day: float | None
    fitness_tss_per_day: float | None
    form_tss_per_day: float | None


@dataclass(frozen=True)
class DashboardTrainingSection:
    metadata: DashboardSectionMetadata
    workout_name: str | None
    workout_goal: str | None
    estimated_duration_minutes: int | None
    target_tss: float | None
    target_if: float | None
    decision_action: str | None
    decision_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DashboardNutritionSection:
    metadata: DashboardSectionMetadata
    observed_daily_expenditure_kcal: float | None
    estimated_daily_requirement_kcal: float | None
    carbohydrate_target_g: float | None
    protein_target_g: float | None
    carbohydrate_target_g_per_kg: float | None
    protein_target_g_per_kg: float | None
    hydration_daily_ml: float | None
    hydration_during_workout_ml_per_hour: float | None
    fueling_pre_workout_carbohydrate_g: float | None
    fueling_during_workout_carbohydrate_g_per_hour: float | None
    fueling_post_workout_carbohydrate_g: float | None
    fueling_post_workout_protein_g: float | None


@dataclass(frozen=True)
class DashboardBodyCompositionSection:
    metadata: DashboardSectionMetadata
    current_body_mass_kg: float | None
    body_fat_percent: float | None
    muscle_mass_kg: float | None
    body_water_percent: float | None
    visceral_fat_rating: float | None
    basal_metabolic_rate_kcal: float | None
    waist_circumference_cm: float | None
    trend_baseline_body_mass_kg: float | None
    trend_period_days: int | None
    trend_absolute_change_kg: float | None
    trend_percentage_change: float | None


@dataclass(frozen=True)
class DashboardGoalSection:
    metadata: DashboardSectionMetadata
    goal_type: str | None
    target_body_mass_kg: float | None
    valid_from: date | None
    valid_until: date | None


@dataclass(frozen=True)
class DashboardRecommendationItem:
    id: str
    recommendation_type: str
    priority: str
    source_confidence: float
    message: str
    evidence: tuple[str, ...]
    source_rules: tuple[str, ...]
    as_of: datetime


@dataclass(frozen=True)
class DashboardRecommendationsSection:
    metadata: DashboardSectionMetadata
    items: tuple[DashboardRecommendationItem, ...] = ()


@dataclass(frozen=True)
class DashboardDataQualitySection:
    metadata: DashboardSectionMetadata
    body_composition_status: str | None
    nutrition_status: str | None
    goal_status: str | None
    trend_quality_status: str | None
    global_limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class AthleteDashboard:
    contract_version: str
    valid_for_date: date
    as_of: datetime
    health: DashboardHealthSection
    recovery: DashboardRecoverySection
    performance: DashboardPerformanceSection
    training: DashboardTrainingSection
    nutrition: DashboardNutritionSection
    body_composition: DashboardBodyCompositionSection
    goal: DashboardGoalSection
    recommendations: DashboardRecommendationsSection
    data_quality: DashboardDataQualitySection
