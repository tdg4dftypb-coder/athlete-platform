from dataclasses import MISSING, FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime

import pytest

import dashboard
from dashboard import (
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


def test_contract_version_and_section_status_are_stable():
    assert DASHBOARD_CONTRACT_VERSION == "1.0"
    assert tuple(DashboardSectionStatus) == (
        DashboardSectionStatus.READY,
        DashboardSectionStatus.PARTIAL,
        DashboardSectionStatus.UNAVAILABLE,
    )
    assert tuple(item.value for item in DashboardSectionStatus) == (
        "ready",
        "partial",
        "unavailable",
    )


def test_metadata_uses_completeness_score_without_legacy_confidence_or_title():
    assert tuple(field.name for field in fields(DashboardSectionMetadata)) == (
        "status",
        "completeness_score",
        "limitations",
        "evidence",
    )
    assert "confidence" not in DashboardSectionMetadata.__annotations__
    assert "title" not in DashboardSectionMetadata.__annotations__


@pytest.mark.parametrize(
    ("model", "expected_fields"),
    (
        (
            DashboardHealthSection,
            (
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
            ),
        ),
        (
            DashboardRecoverySection,
            ("metadata", "recovery_score", "sleep_score"),
        ),
        (
            DashboardPerformanceSection,
            (
                "metadata",
                "weekly_training_load_tss",
                "monthly_training_load_tss",
                "fatigue_tss_per_day",
                "fitness_tss_per_day",
                "form_tss_per_day",
            ),
        ),
        (
            DashboardTrainingSection,
            (
                "metadata",
                "workout_name",
                "workout_goal",
                "estimated_duration_minutes",
                "target_tss",
                "target_if",
                "decision_action",
                "decision_reasons",
            ),
        ),
        (
            DashboardNutritionSection,
            (
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
            ),
        ),
        (
            DashboardBodyCompositionSection,
            (
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
            ),
        ),
        (
            DashboardGoalSection,
            (
                "metadata",
                "goal_type",
                "target_body_mass_kg",
                "valid_from",
                "valid_until",
            ),
        ),
        (
            DashboardRecommendationItem,
            (
                "id",
                "recommendation_type",
                "priority",
                "source_confidence",
                "message",
                "evidence",
                "source_rules",
                "as_of",
            ),
        ),
        (
            DashboardRecommendationsSection,
            ("metadata", "items"),
        ),
        (
            DashboardDataQualitySection,
            (
                "metadata",
                "body_composition_status",
                "nutrition_status",
                "goal_status",
                "trend_quality_status",
                "global_limitations",
            ),
        ),
    ),
)
def test_typed_sections_have_exact_fields(model, expected_fields):
    assert tuple(field.name for field in fields(model)) == expected_fields


def test_athlete_dashboard_has_required_versioned_and_dated_contract():
    assert tuple(field.name for field in fields(AthleteDashboard)) == (
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
    assert all(
        field.default is MISSING and field.default_factory is MISSING
        for field in fields(AthleteDashboard)
    )


def test_all_dashboard_models_are_frozen_and_hashable():
    result = dashboard.DashboardEngine().build(
        valid_for_date=date(2026, 8, 3),
        as_of=datetime(2026, 8, 3, 6),
        health=None,
        recovery=None,
        performance=None,
        decision=None,
        planned_workout=None,
        nutrition=None,
        body_composition=None,
        body_mass_trend_quality=None,
        goal=None,
        recommendation_result=None,
        explainability=None,
    )
    item = DashboardRecommendationItem(
        id="recommendation-1",
        recommendation_type="increase_hydration",
        priority="medium",
        source_confidence=0.8,
        message="Increase hydration.",
        evidence=("water",),
        source_rules=("Rule",),
        as_of=datetime(2026, 8, 3, 6),
    )
    values = (
        result,
        result.health,
        result.recovery,
        result.performance,
        result.training,
        result.nutrition,
        result.body_composition,
        result.goal,
        result.recommendations,
        result.data_quality,
        result.health.metadata,
        item,
        DashboardRecommendationsSection(result.recommendations.metadata, (item,)),
    )

    for value in values:
        assert is_dataclass(value)
        assert value.__dataclass_params__.frozen is True
        hash(value)
    with pytest.raises(FrozenInstanceError):
        result.contract_version = "2.0"


def test_tuple_defaults_are_immutable_and_not_lists():
    metadata = DashboardSectionMetadata(
        status=DashboardSectionStatus.READY,
        completeness_score=None,
    )
    recommendations = DashboardRecommendationsSection(metadata=metadata)

    assert metadata.limitations == ()
    assert metadata.evidence == ()
    assert recommendations.items == ()
    assert isinstance(metadata.limitations, tuple)
    assert isinstance(metadata.evidence, tuple)
    assert isinstance(recommendations.items, tuple)


def test_all_collection_payload_contracts_use_tuples():
    assert DashboardSectionMetadata.__annotations__["limitations"] == (
        "tuple[str, ...]"
    )
    assert DashboardSectionMetadata.__annotations__["evidence"] == (
        "tuple[str, ...]"
    )
    assert DashboardTrainingSection.__annotations__["decision_reasons"] == (
        "tuple[str, ...]"
    )
    assert DashboardRecommendationItem.__annotations__["evidence"] == (
        "tuple[str, ...]"
    )
    assert DashboardRecommendationItem.__annotations__["source_rules"] == (
        "tuple[str, ...]"
    )
    assert DashboardRecommendationsSection.__annotations__["items"] == (
        "tuple[DashboardRecommendationItem, ...]"
    )


def test_generic_dashboard_section_contract_no_longer_exists():
    assert not hasattr(dashboard, "DashboardSection")
    with pytest.raises(ImportError):
        exec("from dashboard import DashboardSection", {})


def test_dashboard_public_exports_are_exact():
    assert dashboard.__all__ == [
        "AthleteDashboard",
        "DASHBOARD_CONTRACT_VERSION",
        "DashboardBodyCompositionSection",
        "DashboardDataQualitySection",
        "DashboardEngine",
        "DashboardGoalSection",
        "DashboardHealthSection",
        "DashboardNutritionSection",
        "DashboardPerformanceSection",
        "DashboardRecommendationItem",
        "DashboardRecommendationsSection",
        "DashboardRecoverySection",
        "DashboardSectionMetadata",
        "DashboardSectionStatus",
        "DashboardTrainingSection",
    ]
    for name in dashboard.__all__:
        assert getattr(dashboard, name) is not None
