from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from math import isfinite

from adaptive.models import (
    AthleteGoalType,
    BodyMassTrendQualityDataStatus,
    GoalAssessmentDataStatus,
)
from body_composition.models import BodyCompositionDataStatus
from dashboard.models import (
    DASHBOARD_CONTRACT_VERSION,
    AthleteDashboard,
    DashboardBodyCompositionSection,
    DashboardDataQualitySection,
    DashboardGoalSection,
    DashboardHealthSection,
    DashboardNutritionSection,
    DashboardPerformanceSection,
    DashboardRecommendationItem,
    DashboardRecommendationsSection,
    DashboardRecoverySection,
    DashboardSectionMetadata,
    DashboardSectionStatus,
    DashboardTrainingSection,
)
from decision.prescription.models import DecisionReason, TrainingObjective
from nutrition.models import NutritionDataStatus
from recommendation.models import RecommendationPriority, RecommendationType
from workout.enums import WorkoutType


__all__ = [
    "DashboardPayloadError",
    "DashboardSerializer",
    "UnsupportedDashboardContractVersion",
]


class DashboardPayloadError(ValueError):
    """The payload does not satisfy the strict Dashboard contract v1.0."""


class UnsupportedDashboardContractVersion(DashboardPayloadError):
    """The payload or model uses an unsupported Dashboard contract version."""


_METADATA_KEYS = (
    "status",
    "completeness_score",
    "limitations",
    "evidence",
)
_TOP_LEVEL_KEYS = (
    "contract_version",
    "valid_for_date",
    "as_of",
    "health",
    "recovery",
    "performance",
    "training",
    "nutrition",
    "body_composition",
    "goal",
    "recommendations",
    "data_quality",
)
_HEALTH_KEYS = (
    "metadata",
    "hrv_ms",
    "resting_heart_rate_bpm",
    "sleep_minutes",
    "steps",
    "active_energy_kcal",
    "resting_energy_kcal",
    "respiratory_rate_per_minute",
    "oxygen_saturation_percent",
    "wrist_temperature_celsius",
)
_RECOVERY_KEYS = ("metadata", "recovery_score", "sleep_score")
_PERFORMANCE_KEYS = (
    "metadata",
    "weekly_training_load_tss",
    "monthly_training_load_tss",
    "fatigue_tss_per_day",
    "fitness_tss_per_day",
    "form_tss_per_day",
)
_TRAINING_KEYS = (
    "metadata",
    "workout_name",
    "workout_goal",
    "estimated_duration_minutes",
    "target_tss",
    "target_if",
    "decision_action",
    "decision_reasons",
)
_NUTRITION_KEYS = (
    "metadata",
    "observed_daily_expenditure_kcal",
    "estimated_daily_requirement_kcal",
    "carbohydrate_target_g",
    "protein_target_g",
    "carbohydrate_target_g_per_kg",
    "protein_target_g_per_kg",
    "hydration_daily_ml",
    "hydration_during_workout_ml_per_hour",
    "fueling_pre_workout_carbohydrate_g",
    "fueling_during_workout_carbohydrate_g_per_hour",
    "fueling_post_workout_carbohydrate_g",
    "fueling_post_workout_protein_g",
)
_BODY_COMPOSITION_KEYS = (
    "metadata",
    "current_body_mass_kg",
    "body_fat_percent",
    "muscle_mass_kg",
    "body_water_percent",
    "visceral_fat_rating",
    "basal_metabolic_rate_kcal",
    "waist_circumference_cm",
    "trend_baseline_body_mass_kg",
    "trend_period_days",
    "trend_absolute_change_kg",
    "trend_percentage_change",
)
_GOAL_KEYS = (
    "metadata",
    "goal_type",
    "target_body_mass_kg",
    "valid_from",
    "valid_until",
)
_RECOMMENDATIONS_KEYS = ("metadata", "items")
_RECOMMENDATION_ITEM_KEYS = (
    "id",
    "recommendation_type",
    "priority",
    "source_confidence",
    "message",
    "evidence",
    "source_rules",
    "as_of",
)
_DATA_QUALITY_KEYS = (
    "metadata",
    "body_composition_status",
    "nutrition_status",
    "goal_status",
    "trend_quality_status",
    "global_limitations",
)

_SECTION_STATUS_VALUES = frozenset(item.value for item in DashboardSectionStatus)
_GOAL_TYPE_VALUES = frozenset(item.value for item in AthleteGoalType)
_BODY_STATUS_VALUES = frozenset(item.value for item in BodyCompositionDataStatus)
_NUTRITION_STATUS_VALUES = frozenset(item.value for item in NutritionDataStatus)
_GOAL_STATUS_VALUES = frozenset(item.value for item in GoalAssessmentDataStatus)
_TREND_STATUS_VALUES = frozenset(
    item.value for item in BodyMassTrendQualityDataStatus
)
_RECOMMENDATION_TYPE_VALUES = frozenset(
    item.value for item in RecommendationType
)
_RECOMMENDATION_PRIORITY_VALUES = frozenset(
    item.value for item in RecommendationPriority
)
_TRAINING_OBJECTIVE_VALUES = frozenset(item.value for item in TrainingObjective)
_WORKOUT_TYPE_VALUES = frozenset(item.value for item in WorkoutType)
_DECISION_REASON_VALUES = frozenset(item.value for item in DecisionReason)


class DashboardSerializer:
    """Serialize and restore the strict, framework-independent v1.0 payload."""

    def serialize(self, dashboard: AthleteDashboard) -> dict[str, object]:
        if not isinstance(dashboard, AthleteDashboard):
            raise TypeError("dashboard must be an AthleteDashboard")
        self._require_supported_version(dashboard.contract_version)

        payload: dict[str, object] = {
            "contract_version": dashboard.contract_version,
            "valid_for_date": dashboard.valid_for_date.isoformat(),
            "as_of": dashboard.as_of.isoformat(),
            "health": self._serialize_health(dashboard.health),
            "recovery": self._serialize_recovery(dashboard.recovery),
            "performance": self._serialize_performance(dashboard.performance),
            "training": self._serialize_training(dashboard.training),
            "nutrition": self._serialize_nutrition(dashboard.nutrition),
            "body_composition": self._serialize_body_composition(
                dashboard.body_composition
            ),
            "goal": self._serialize_goal(dashboard.goal),
            "recommendations": self._serialize_recommendations(
                dashboard.recommendations
            ),
            "data_quality": self._serialize_data_quality(
                dashboard.data_quality
            ),
        }
        self.deserialize(payload)
        return payload

    def deserialize(self, payload: Mapping[str, object]) -> AthleteDashboard:
        root = _mapping(payload, "dashboard")
        _require_exact_keys(root, _TOP_LEVEL_KEYS, "dashboard")
        version = _string(root["contract_version"], "dashboard.contract_version")
        self._require_supported_version(version)

        return AthleteDashboard(
            contract_version=version,
            valid_for_date=_date(root["valid_for_date"], "dashboard.valid_for_date"),
            as_of=_datetime(root["as_of"], "dashboard.as_of"),
            health=self._deserialize_health(root["health"]),
            recovery=self._deserialize_recovery(root["recovery"]),
            performance=self._deserialize_performance(root["performance"]),
            training=self._deserialize_training(root["training"]),
            nutrition=self._deserialize_nutrition(root["nutrition"]),
            body_composition=self._deserialize_body_composition(
                root["body_composition"]
            ),
            goal=self._deserialize_goal(root["goal"]),
            recommendations=self._deserialize_recommendations(
                root["recommendations"]
            ),
            data_quality=self._deserialize_data_quality(root["data_quality"]),
        )

    @staticmethod
    def _require_supported_version(version: object) -> None:
        if version != DASHBOARD_CONTRACT_VERSION:
            raise UnsupportedDashboardContractVersion(
                f"unsupported dashboard contract version: {version!r}"
            )

    @staticmethod
    def _serialize_metadata(
        metadata: DashboardSectionMetadata,
    ) -> dict[str, object]:
        return {
            "status": metadata.status.value,
            "completeness_score": _serialized_number(
                metadata.completeness_score,
                "metadata.completeness_score",
            ),
            "limitations": list(metadata.limitations),
            "evidence": list(metadata.evidence),
        }

    @classmethod
    def _serialize_health(
        cls,
        section: DashboardHealthSection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "hrv_ms": section.hrv_ms,
            "resting_heart_rate_bpm": section.resting_heart_rate_bpm,
            "sleep_minutes": section.sleep_minutes,
            "steps": section.steps,
            "active_energy_kcal": section.active_energy_kcal,
            "resting_energy_kcal": section.resting_energy_kcal,
            "respiratory_rate_per_minute": section.respiratory_rate_per_minute,
            "oxygen_saturation_percent": section.oxygen_saturation_percent,
            "wrist_temperature_celsius": section.wrist_temperature_celsius,
        }

    @classmethod
    def _serialize_recovery(
        cls,
        section: DashboardRecoverySection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "recovery_score": section.recovery_score,
            "sleep_score": section.sleep_score,
        }

    @classmethod
    def _serialize_performance(
        cls,
        section: DashboardPerformanceSection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "weekly_training_load_tss": section.weekly_training_load_tss,
            "monthly_training_load_tss": section.monthly_training_load_tss,
            "fatigue_tss_per_day": section.fatigue_tss_per_day,
            "fitness_tss_per_day": section.fitness_tss_per_day,
            "form_tss_per_day": section.form_tss_per_day,
        }

    @classmethod
    def _serialize_training(
        cls,
        section: DashboardTrainingSection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "workout_name": section.workout_name,
            "workout_goal": section.workout_goal,
            "estimated_duration_minutes": section.estimated_duration_minutes,
            "target_tss": section.target_tss,
            "target_if": section.target_if,
            "decision_action": section.decision_action,
            "decision_reasons": list(section.decision_reasons),
        }

    @classmethod
    def _serialize_nutrition(
        cls,
        section: DashboardNutritionSection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "observed_daily_expenditure_kcal": (
                section.observed_daily_expenditure_kcal
            ),
            "estimated_daily_requirement_kcal": (
                section.estimated_daily_requirement_kcal
            ),
            "carbohydrate_target_g": section.carbohydrate_target_g,
            "protein_target_g": section.protein_target_g,
            "carbohydrate_target_g_per_kg": (
                section.carbohydrate_target_g_per_kg
            ),
            "protein_target_g_per_kg": section.protein_target_g_per_kg,
            "hydration_daily_ml": section.hydration_daily_ml,
            "hydration_during_workout_ml_per_hour": (
                section.hydration_during_workout_ml_per_hour
            ),
            "fueling_pre_workout_carbohydrate_g": (
                section.fueling_pre_workout_carbohydrate_g
            ),
            "fueling_during_workout_carbohydrate_g_per_hour": (
                section.fueling_during_workout_carbohydrate_g_per_hour
            ),
            "fueling_post_workout_carbohydrate_g": (
                section.fueling_post_workout_carbohydrate_g
            ),
            "fueling_post_workout_protein_g": (
                section.fueling_post_workout_protein_g
            ),
        }

    @classmethod
    def _serialize_body_composition(
        cls,
        section: DashboardBodyCompositionSection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "current_body_mass_kg": section.current_body_mass_kg,
            "body_fat_percent": section.body_fat_percent,
            "muscle_mass_kg": section.muscle_mass_kg,
            "body_water_percent": section.body_water_percent,
            "visceral_fat_rating": section.visceral_fat_rating,
            "basal_metabolic_rate_kcal": section.basal_metabolic_rate_kcal,
            "waist_circumference_cm": section.waist_circumference_cm,
            "trend_baseline_body_mass_kg": (
                section.trend_baseline_body_mass_kg
            ),
            "trend_period_days": section.trend_period_days,
            "trend_absolute_change_kg": section.trend_absolute_change_kg,
            "trend_percentage_change": section.trend_percentage_change,
        }

    @classmethod
    def _serialize_goal(
        cls,
        section: DashboardGoalSection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "goal_type": section.goal_type,
            "target_body_mass_kg": section.target_body_mass_kg,
            "valid_from": (
                section.valid_from.isoformat()
                if section.valid_from is not None
                else None
            ),
            "valid_until": (
                section.valid_until.isoformat()
                if section.valid_until is not None
                else None
            ),
        }

    @classmethod
    def _serialize_recommendations(
        cls,
        section: DashboardRecommendationsSection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "items": [
                {
                    "id": item.id,
                    "recommendation_type": item.recommendation_type,
                    "priority": item.priority,
                    "source_confidence": _serialized_number(
                        item.source_confidence,
                        "recommendations.items.source_confidence",
                    ),
                    "message": item.message,
                    "evidence": list(item.evidence),
                    "source_rules": list(item.source_rules),
                    "as_of": item.as_of.isoformat(),
                }
                for item in section.items
            ],
        }

    @classmethod
    def _serialize_data_quality(
        cls,
        section: DashboardDataQualitySection,
    ) -> dict[str, object]:
        return {
            "metadata": cls._serialize_metadata(section.metadata),
            "body_composition_status": section.body_composition_status,
            "nutrition_status": section.nutrition_status,
            "goal_status": section.goal_status,
            "trend_quality_status": section.trend_quality_status,
            "global_limitations": list(section.global_limitations),
        }

    @staticmethod
    def _deserialize_metadata(
        value: object,
        path: str,
    ) -> DashboardSectionMetadata:
        data = _mapping(value, path)
        _require_exact_keys(data, _METADATA_KEYS, path)
        status_value = _enum_string(
            data["status"],
            _SECTION_STATUS_VALUES,
            f"{path}.status",
        )
        return DashboardSectionMetadata(
            status=DashboardSectionStatus(status_value),
            completeness_score=_optional_number(
                data["completeness_score"],
                f"{path}.completeness_score",
            ),
            limitations=_string_tuple(data["limitations"], f"{path}.limitations"),
            evidence=_string_tuple(data["evidence"], f"{path}.evidence"),
        )

    @classmethod
    def _deserialize_health(cls, value: object) -> DashboardHealthSection:
        path = "dashboard.health"
        data = _section(value, _HEALTH_KEYS, path)
        return DashboardHealthSection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            hrv_ms=_optional_number(data["hrv_ms"], f"{path}.hrv_ms"),
            resting_heart_rate_bpm=_optional_number(
                data["resting_heart_rate_bpm"],
                f"{path}.resting_heart_rate_bpm",
            ),
            sleep_minutes=_optional_int(data["sleep_minutes"], f"{path}.sleep_minutes"),
            steps=_optional_int(data["steps"], f"{path}.steps"),
            active_energy_kcal=_optional_number(
                data["active_energy_kcal"], f"{path}.active_energy_kcal"
            ),
            resting_energy_kcal=_optional_number(
                data["resting_energy_kcal"], f"{path}.resting_energy_kcal"
            ),
            respiratory_rate_per_minute=_optional_number(
                data["respiratory_rate_per_minute"],
                f"{path}.respiratory_rate_per_minute",
            ),
            oxygen_saturation_percent=_optional_number(
                data["oxygen_saturation_percent"],
                f"{path}.oxygen_saturation_percent",
            ),
            wrist_temperature_celsius=_optional_number(
                data["wrist_temperature_celsius"],
                f"{path}.wrist_temperature_celsius",
            ),
        )

    @classmethod
    def _deserialize_recovery(cls, value: object) -> DashboardRecoverySection:
        path = "dashboard.recovery"
        data = _section(value, _RECOVERY_KEYS, path)
        return DashboardRecoverySection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            recovery_score=_optional_int(
                data["recovery_score"], f"{path}.recovery_score"
            ),
            sleep_score=_optional_int(data["sleep_score"], f"{path}.sleep_score"),
        )

    @classmethod
    def _deserialize_performance(
        cls,
        value: object,
    ) -> DashboardPerformanceSection:
        path = "dashboard.performance"
        data = _section(value, _PERFORMANCE_KEYS, path)
        return DashboardPerformanceSection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            weekly_training_load_tss=_optional_number(
                data["weekly_training_load_tss"],
                f"{path}.weekly_training_load_tss",
            ),
            monthly_training_load_tss=_optional_number(
                data["monthly_training_load_tss"],
                f"{path}.monthly_training_load_tss",
            ),
            fatigue_tss_per_day=_optional_number(
                data["fatigue_tss_per_day"], f"{path}.fatigue_tss_per_day"
            ),
            fitness_tss_per_day=_optional_number(
                data["fitness_tss_per_day"], f"{path}.fitness_tss_per_day"
            ),
            form_tss_per_day=_optional_number(
                data["form_tss_per_day"], f"{path}.form_tss_per_day"
            ),
        )

    @classmethod
    def _deserialize_training(cls, value: object) -> DashboardTrainingSection:
        path = "dashboard.training"
        data = _section(value, _TRAINING_KEYS, path)
        return DashboardTrainingSection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            workout_name=_optional_string(
                data["workout_name"], f"{path}.workout_name"
            ),
            workout_goal=_optional_enum_string(
                data["workout_goal"],
                _TRAINING_OBJECTIVE_VALUES,
                f"{path}.workout_goal",
            ),
            estimated_duration_minutes=_optional_int(
                data["estimated_duration_minutes"],
                f"{path}.estimated_duration_minutes",
            ),
            target_tss=_optional_number(data["target_tss"], f"{path}.target_tss"),
            target_if=_optional_number(data["target_if"], f"{path}.target_if"),
            decision_action=_optional_enum_string(
                data["decision_action"],
                _WORKOUT_TYPE_VALUES,
                f"{path}.decision_action",
            ),
            decision_reasons=_enum_string_tuple(
                data["decision_reasons"],
                _DECISION_REASON_VALUES,
                f"{path}.decision_reasons",
            ),
        )

    @classmethod
    def _deserialize_nutrition(cls, value: object) -> DashboardNutritionSection:
        path = "dashboard.nutrition"
        data = _section(value, _NUTRITION_KEYS, path)
        return DashboardNutritionSection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            observed_daily_expenditure_kcal=_optional_number(
                data["observed_daily_expenditure_kcal"],
                f"{path}.observed_daily_expenditure_kcal",
            ),
            estimated_daily_requirement_kcal=_optional_number(
                data["estimated_daily_requirement_kcal"],
                f"{path}.estimated_daily_requirement_kcal",
            ),
            carbohydrate_target_g=_optional_number(
                data["carbohydrate_target_g"], f"{path}.carbohydrate_target_g"
            ),
            protein_target_g=_optional_number(
                data["protein_target_g"], f"{path}.protein_target_g"
            ),
            carbohydrate_target_g_per_kg=_optional_number(
                data["carbohydrate_target_g_per_kg"],
                f"{path}.carbohydrate_target_g_per_kg",
            ),
            protein_target_g_per_kg=_optional_number(
                data["protein_target_g_per_kg"],
                f"{path}.protein_target_g_per_kg",
            ),
            hydration_daily_ml=_optional_number(
                data["hydration_daily_ml"], f"{path}.hydration_daily_ml"
            ),
            hydration_during_workout_ml_per_hour=_optional_number(
                data["hydration_during_workout_ml_per_hour"],
                f"{path}.hydration_during_workout_ml_per_hour",
            ),
            fueling_pre_workout_carbohydrate_g=_optional_number(
                data["fueling_pre_workout_carbohydrate_g"],
                f"{path}.fueling_pre_workout_carbohydrate_g",
            ),
            fueling_during_workout_carbohydrate_g_per_hour=_optional_number(
                data["fueling_during_workout_carbohydrate_g_per_hour"],
                f"{path}.fueling_during_workout_carbohydrate_g_per_hour",
            ),
            fueling_post_workout_carbohydrate_g=_optional_number(
                data["fueling_post_workout_carbohydrate_g"],
                f"{path}.fueling_post_workout_carbohydrate_g",
            ),
            fueling_post_workout_protein_g=_optional_number(
                data["fueling_post_workout_protein_g"],
                f"{path}.fueling_post_workout_protein_g",
            ),
        )

    @classmethod
    def _deserialize_body_composition(
        cls,
        value: object,
    ) -> DashboardBodyCompositionSection:
        path = "dashboard.body_composition"
        data = _section(value, _BODY_COMPOSITION_KEYS, path)
        return DashboardBodyCompositionSection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            current_body_mass_kg=_optional_number(
                data["current_body_mass_kg"], f"{path}.current_body_mass_kg"
            ),
            body_fat_percent=_optional_number(
                data["body_fat_percent"], f"{path}.body_fat_percent"
            ),
            muscle_mass_kg=_optional_number(
                data["muscle_mass_kg"], f"{path}.muscle_mass_kg"
            ),
            body_water_percent=_optional_number(
                data["body_water_percent"], f"{path}.body_water_percent"
            ),
            visceral_fat_rating=_optional_number(
                data["visceral_fat_rating"], f"{path}.visceral_fat_rating"
            ),
            basal_metabolic_rate_kcal=_optional_number(
                data["basal_metabolic_rate_kcal"],
                f"{path}.basal_metabolic_rate_kcal",
            ),
            waist_circumference_cm=_optional_number(
                data["waist_circumference_cm"],
                f"{path}.waist_circumference_cm",
            ),
            trend_baseline_body_mass_kg=_optional_number(
                data["trend_baseline_body_mass_kg"],
                f"{path}.trend_baseline_body_mass_kg",
            ),
            trend_period_days=_optional_int(
                data["trend_period_days"], f"{path}.trend_period_days"
            ),
            trend_absolute_change_kg=_optional_number(
                data["trend_absolute_change_kg"],
                f"{path}.trend_absolute_change_kg",
            ),
            trend_percentage_change=_optional_number(
                data["trend_percentage_change"],
                f"{path}.trend_percentage_change",
            ),
        )

    @classmethod
    def _deserialize_goal(cls, value: object) -> DashboardGoalSection:
        path = "dashboard.goal"
        data = _section(value, _GOAL_KEYS, path)
        return DashboardGoalSection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            goal_type=_optional_enum_string(
                data["goal_type"], _GOAL_TYPE_VALUES, f"{path}.goal_type"
            ),
            target_body_mass_kg=_optional_number(
                data["target_body_mass_kg"], f"{path}.target_body_mass_kg"
            ),
            valid_from=_optional_date(data["valid_from"], f"{path}.valid_from"),
            valid_until=_optional_date(data["valid_until"], f"{path}.valid_until"),
        )

    @classmethod
    def _deserialize_recommendations(
        cls,
        value: object,
    ) -> DashboardRecommendationsSection:
        path = "dashboard.recommendations"
        data = _section(value, _RECOMMENDATIONS_KEYS, path)
        items_value = data["items"]
        if not isinstance(items_value, list):
            raise DashboardPayloadError(f"{path}.items must be a list")

        items = tuple(
            cls._deserialize_recommendation_item(item, index)
            for index, item in enumerate(items_value)
        )
        return DashboardRecommendationsSection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            items=items,
        )

    @staticmethod
    def _deserialize_recommendation_item(
        value: object,
        index: int,
    ) -> DashboardRecommendationItem:
        path = f"dashboard.recommendations.items[{index}]"
        data = _section(value, _RECOMMENDATION_ITEM_KEYS, path)
        return DashboardRecommendationItem(
            id=_string(data["id"], f"{path}.id"),
            recommendation_type=_enum_string(
                data["recommendation_type"],
                _RECOMMENDATION_TYPE_VALUES,
                f"{path}.recommendation_type",
            ),
            priority=_enum_string(
                data["priority"],
                _RECOMMENDATION_PRIORITY_VALUES,
                f"{path}.priority",
            ),
            source_confidence=_number(
                data["source_confidence"], f"{path}.source_confidence"
            ),
            message=_string(data["message"], f"{path}.message"),
            evidence=_string_tuple(data["evidence"], f"{path}.evidence"),
            source_rules=_string_tuple(
                data["source_rules"], f"{path}.source_rules"
            ),
            as_of=_datetime(data["as_of"], f"{path}.as_of"),
        )

    @classmethod
    def _deserialize_data_quality(
        cls,
        value: object,
    ) -> DashboardDataQualitySection:
        path = "dashboard.data_quality"
        data = _section(value, _DATA_QUALITY_KEYS, path)
        return DashboardDataQualitySection(
            metadata=cls._deserialize_metadata(data["metadata"], f"{path}.metadata"),
            body_composition_status=_optional_enum_string(
                data["body_composition_status"],
                _BODY_STATUS_VALUES,
                f"{path}.body_composition_status",
            ),
            nutrition_status=_optional_enum_string(
                data["nutrition_status"],
                _NUTRITION_STATUS_VALUES,
                f"{path}.nutrition_status",
            ),
            goal_status=_optional_enum_string(
                data["goal_status"],
                _GOAL_STATUS_VALUES,
                f"{path}.goal_status",
            ),
            trend_quality_status=_optional_enum_string(
                data["trend_quality_status"],
                _TREND_STATUS_VALUES,
                f"{path}.trend_quality_status",
            ),
            global_limitations=_string_tuple(
                data["global_limitations"], f"{path}.global_limitations"
            ),
        )


def _mapping(value: object, path: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise DashboardPayloadError(f"{path} must be an object")
    return value


def _section(
    value: object,
    keys: tuple[str, ...],
    path: str,
) -> Mapping[object, object]:
    data = _mapping(value, path)
    _require_exact_keys(data, keys, path)
    return data


def _require_exact_keys(
    value: Mapping[object, object],
    expected: tuple[str, ...],
    path: str,
) -> None:
    expected_set = set(expected)
    missing = [key for key in expected if key not in value]
    unknown = sorted(repr(key) for key in value if key not in expected_set)
    if missing:
        raise DashboardPayloadError(
            f"{path} is missing required fields: {', '.join(missing)}"
        )
    if unknown:
        raise DashboardPayloadError(
            f"{path} contains unknown fields: {', '.join(unknown)}"
        )


def _string(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise DashboardPayloadError(f"{path} must be a string")
    return value


def _optional_string(value: object, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _number(value: object, path: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DashboardPayloadError(f"{path} must be a finite number")
    if not isfinite(value):
        raise DashboardPayloadError(f"{path} must be a finite number")
    return value


def _optional_number(value: object, path: str) -> int | float | None:
    if value is None:
        return None
    return _number(value, path)


def _serialized_number(value: object, path: str) -> int | float | None:
    return _optional_number(value, path)


def _optional_int(value: object, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise DashboardPayloadError(f"{path} must be an integer")
    return value


def _string_tuple(value: object, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise DashboardPayloadError(f"{path} must be a list")
    return tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))


def _enum_string(value: object, allowed: frozenset[str], path: str) -> str:
    result = _string(value, path)
    if result not in allowed:
        raise DashboardPayloadError(f"{path} has unknown enum value: {result!r}")
    return result


def _optional_enum_string(
    value: object,
    allowed: frozenset[str],
    path: str,
) -> str | None:
    if value is None:
        return None
    return _enum_string(value, allowed, path)


def _enum_string_tuple(
    value: object,
    allowed: frozenset[str],
    path: str,
) -> tuple[str, ...]:
    values = _string_tuple(value, path)
    for index, item in enumerate(values):
        if item not in allowed:
            raise DashboardPayloadError(
                f"{path}[{index}] has unknown enum value: {item!r}"
            )
    return values


def _date(value: object, path: str) -> date:
    text = _string(value, path)
    try:
        result = date.fromisoformat(text)
    except ValueError as error:
        raise DashboardPayloadError(f"{path} must be an ISO date") from error
    if result.isoformat() != text:
        raise DashboardPayloadError(f"{path} must use canonical ISO date format")
    return result


def _optional_date(value: object, path: str) -> date | None:
    if value is None:
        return None
    return _date(value, path)


def _datetime(value: object, path: str) -> datetime:
    text = _string(value, path)
    try:
        result = datetime.fromisoformat(text)
    except ValueError as error:
        raise DashboardPayloadError(f"{path} must be an ISO datetime") from error
    if result.isoformat() != text:
        raise DashboardPayloadError(
            f"{path} must use canonical ISO datetime format"
        )
    return result
