from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import json
import math

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
    DashboardPayloadError,
    DashboardPerformanceSection,
    DashboardRecommendationItem,
    DashboardRecommendationsSection,
    DashboardRecoverySection,
    DashboardSectionMetadata,
    DashboardSectionStatus,
    DashboardSerializer,
    DashboardTrainingSection,
    UnsupportedDashboardContractVersion,
)


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6, 30, 15)


def _metadata(
    status: DashboardSectionStatus = DashboardSectionStatus.READY,
    score: float | None = 0.75,
) -> DashboardSectionMetadata:
    return DashboardSectionMetadata(
        status=status,
        completeness_score=score,
        limitations=("limitation:b", "limitation:a"),
        evidence=("evidence:b", "evidence:a"),
    )


def _full_dashboard(*, as_of: datetime = AS_OF) -> AthleteDashboard:
    metadata = _metadata()
    return AthleteDashboard(
        contract_version=DASHBOARD_CONTRACT_VERSION,
        valid_for_date=VALID_FOR_DATE,
        as_of=as_of,
        health=DashboardHealthSection(
            metadata=metadata,
            hrv_ms=42.5,
            resting_heart_rate_bpm=51,
            sleep_minutes=465,
            steps=8200,
            active_energy_kcal=620.0,
            resting_energy_kcal=1780.0,
            respiratory_rate_per_minute=14.2,
            oxygen_saturation_percent=98.0,
            wrist_temperature_celsius=36.1,
        ),
        recovery=DashboardRecoverySection(
            metadata=metadata,
            recovery_score=84,
            sleep_score=91,
        ),
        performance=DashboardPerformanceSection(
            metadata=metadata,
            weekly_training_load_tss=310.0,
            monthly_training_load_tss=1210.0,
            fatigue_tss_per_day=44.3,
            fitness_tss_per_day=28.8,
            form_tss_per_day=-15.5,
        ),
        training=DashboardTrainingSection(
            metadata=metadata,
            workout_name="Endurance 75",
            workout_goal="ENDURANCE",
            estimated_duration_minutes=75,
            target_tss=62.0,
            target_if=None,
            decision_action="endurance",
            decision_reasons=("insight_need_more_recovery",),
        ),
        nutrition=DashboardNutritionSection(
            metadata=metadata,
            observed_daily_expenditure_kcal=2400.0,
            estimated_daily_requirement_kcal=None,
            carbohydrate_target_g=360.0,
            protein_target_g=128.0,
            carbohydrate_target_g_per_kg=4.5,
            protein_target_g_per_kg=1.6,
            hydration_daily_ml=2800.0,
            hydration_during_workout_ml_per_hour=600.0,
            fueling_pre_workout_carbohydrate_g=40.0,
            fueling_during_workout_carbohydrate_g_per_hour=30.0,
            fueling_post_workout_carbohydrate_g=80.0,
            fueling_post_workout_protein_g=24.0,
        ),
        body_composition=DashboardBodyCompositionSection(
            metadata=metadata,
            current_body_mass_kg=80.0,
            body_fat_percent=17.0,
            muscle_mass_kg=61.0,
            body_water_percent=55.0,
            visceral_fat_rating=None,
            basal_metabolic_rate_kcal=1750.0,
            waist_circumference_cm=82.0,
            trend_baseline_body_mass_kg=81.5,
            trend_period_days=28,
            trend_absolute_change_kg=-1.5,
            trend_percentage_change=-1.84,
        ),
        goal=DashboardGoalSection(
            metadata=metadata,
            goal_type="reduce_body_mass",
            target_body_mass_kg=77.0,
            valid_from=date(2026, 7, 1),
            valid_until=date(2026, 10, 1),
        ),
        recommendations=DashboardRecommendationsSection(
            metadata=metadata,
            items=(
                DashboardRecommendationItem(
                    id="hydration",
                    recommendation_type="increase_hydration",
                    priority="high",
                    source_confidence=0.85,
                    message="Increase hydration.",
                    evidence=("water:b", "water:a"),
                    source_rules=("HydrationRule",),
                    as_of=as_of,
                ),
                DashboardRecommendationItem(
                    id="sleep",
                    recommendation_type="extend_sleep",
                    priority="medium",
                    source_confidence=0.7,
                    message="Extend sleep duration.",
                    evidence=("sleep:a",),
                    source_rules=("SleepRule",),
                    as_of=as_of - timedelta(minutes=15),
                ),
            ),
        ),
        data_quality=DashboardDataQualitySection(
            metadata=metadata,
            body_composition_status="complete",
            nutrition_status="complete",
            goal_status="complete",
            trend_quality_status="partial",
            global_limitations=("body:missing_source", "trend:partial"),
        ),
    )


def _unavailable_dashboard(*, as_of: datetime = AS_OF) -> AthleteDashboard:
    metadata = DashboardSectionMetadata(
        status=DashboardSectionStatus.UNAVAILABLE,
        completeness_score=None,
    )
    return AthleteDashboard(
        contract_version=DASHBOARD_CONTRACT_VERSION,
        valid_for_date=VALID_FOR_DATE,
        as_of=as_of,
        health=DashboardHealthSection(
            metadata, None, None, None, None, None, None, None, None, None
        ),
        recovery=DashboardRecoverySection(metadata, None, None),
        performance=DashboardPerformanceSection(metadata, None, None, None, None, None),
        training=DashboardTrainingSection(metadata, None, None, None, None, None, None),
        nutrition=DashboardNutritionSection(
            metadata,
            None, None, None, None, None, None,
            None, None, None, None, None, None,
        ),
        body_composition=DashboardBodyCompositionSection(
            metadata, None, None, None, None, None, None, None, None, None, None, None
        ),
        goal=DashboardGoalSection(metadata, None, None, None, None),
        recommendations=DashboardRecommendationsSection(metadata),
        data_quality=DashboardDataQualitySection(metadata, None, None, None, None),
    )


def test_full_dashboard_serializes_to_exact_snapshot_payload():
    payload = DashboardSerializer().serialize(_full_dashboard())

    assert payload == {
        "contract_version": "1.0",
        "valid_for_date": "2026-08-03",
        "as_of": "2026-08-03T06:30:15",
        "health": {
            "metadata": {
                "status": "ready",
                "completeness_score": 0.75,
                "limitations": ["limitation:b", "limitation:a"],
                "evidence": ["evidence:b", "evidence:a"],
            },
            "hrv_ms": 42.5,
            "resting_heart_rate_bpm": 51,
            "sleep_minutes": 465,
            "steps": 8200,
            "active_energy_kcal": 620.0,
            "resting_energy_kcal": 1780.0,
            "respiratory_rate_per_minute": 14.2,
            "oxygen_saturation_percent": 98.0,
            "wrist_temperature_celsius": 36.1,
        },
        "recovery": {
            "metadata": payload["health"]["metadata"],
            "recovery_score": 84,
            "sleep_score": 91,
        },
        "performance": {
            "metadata": payload["health"]["metadata"],
            "weekly_training_load_tss": 310.0,
            "monthly_training_load_tss": 1210.0,
            "fatigue_tss_per_day": 44.3,
            "fitness_tss_per_day": 28.8,
            "form_tss_per_day": -15.5,
        },
        "training": {
            "metadata": payload["health"]["metadata"],
            "workout_name": "Endurance 75",
            "workout_goal": "ENDURANCE",
            "estimated_duration_minutes": 75,
            "target_tss": 62.0,
            "target_if": None,
            "decision_action": "endurance",
            "decision_reasons": ["insight_need_more_recovery"],
        },
        "nutrition": {
            "metadata": payload["health"]["metadata"],
            "observed_daily_expenditure_kcal": 2400.0,
            "estimated_daily_requirement_kcal": None,
            "carbohydrate_target_g": 360.0,
            "protein_target_g": 128.0,
            "carbohydrate_target_g_per_kg": 4.5,
            "protein_target_g_per_kg": 1.6,
            "hydration_daily_ml": 2800.0,
            "hydration_during_workout_ml_per_hour": 600.0,
            "fueling_pre_workout_carbohydrate_g": 40.0,
            "fueling_during_workout_carbohydrate_g_per_hour": 30.0,
            "fueling_post_workout_carbohydrate_g": 80.0,
            "fueling_post_workout_protein_g": 24.0,
        },
        "body_composition": {
            "metadata": payload["health"]["metadata"],
            "current_body_mass_kg": 80.0,
            "body_fat_percent": 17.0,
            "muscle_mass_kg": 61.0,
            "body_water_percent": 55.0,
            "visceral_fat_rating": None,
            "basal_metabolic_rate_kcal": 1750.0,
            "waist_circumference_cm": 82.0,
            "trend_baseline_body_mass_kg": 81.5,
            "trend_period_days": 28,
            "trend_absolute_change_kg": -1.5,
            "trend_percentage_change": -1.84,
        },
        "goal": {
            "metadata": payload["health"]["metadata"],
            "goal_type": "reduce_body_mass",
            "target_body_mass_kg": 77.0,
            "valid_from": "2026-07-01",
            "valid_until": "2026-10-01",
        },
        "recommendations": {
            "metadata": payload["health"]["metadata"],
            "items": [
                {
                    "id": "hydration",
                    "recommendation_type": "increase_hydration",
                    "priority": "high",
                    "source_confidence": 0.85,
                    "message": "Increase hydration.",
                    "evidence": ["water:b", "water:a"],
                    "source_rules": ["HydrationRule"],
                    "as_of": "2026-08-03T06:30:15",
                },
                {
                    "id": "sleep",
                    "recommendation_type": "extend_sleep",
                    "priority": "medium",
                    "source_confidence": 0.7,
                    "message": "Extend sleep duration.",
                    "evidence": ["sleep:a"],
                    "source_rules": ["SleepRule"],
                    "as_of": "2026-08-03T06:15:15",
                },
            ],
        },
        "data_quality": {
            "metadata": payload["health"]["metadata"],
            "body_composition_status": "complete",
            "nutrition_status": "complete",
            "goal_status": "complete",
            "trend_quality_status": "partial",
            "global_limitations": ["body:missing_source", "trend:partial"],
        },
    }


def test_payload_has_exact_keys_for_top_level_sections_and_metadata():
    payload = DashboardSerializer().serialize(_full_dashboard())

    assert tuple(payload) == (
        "contract_version", "valid_for_date", "as_of", "health", "recovery",
        "performance", "training", "nutrition", "body_composition", "goal",
        "recommendations", "data_quality",
    )
    assert set(payload["health"]["metadata"]) == {
        "status", "completeness_score", "limitations", "evidence"
    }
    assert set(payload["recommendations"]["items"][0]) == {
        "id", "recommendation_type", "priority", "source_confidence",
        "message", "evidence", "source_rules", "as_of",
    }


def test_payload_contains_only_json_safe_primitives():
    payload = DashboardSerializer().serialize(_full_dashboard())

    encoded = json.dumps(payload, allow_nan=False)

    assert json.loads(encoded) == payload


def test_serialization_preserves_order_and_does_not_mutate_dashboard():
    model = _full_dashboard()
    before = deepcopy(model)

    payload = DashboardSerializer().serialize(model)

    assert model == before
    assert [item["id"] for item in payload["recommendations"]["items"]] == [
        "hydration", "sleep"
    ]
    assert payload["health"]["metadata"]["limitations"] == [
        "limitation:b", "limitation:a"
    ]


@pytest.mark.parametrize(
    "as_of",
    (
        AS_OF,
        AS_OF.replace(tzinfo=timezone(timedelta(hours=2))),
    ),
)
def test_full_dashboard_round_trip_preserves_naive_or_aware_datetime(as_of):
    serializer = DashboardSerializer()
    model = _full_dashboard(as_of=as_of)

    restored = serializer.deserialize(serializer.serialize(model))

    assert restored == model
    assert restored.as_of.tzinfo == as_of.tzinfo


def test_unavailable_sections_none_and_empty_recommendations_round_trip():
    serializer = DashboardSerializer()
    model = _unavailable_dashboard()

    payload = serializer.serialize(model)
    restored = serializer.deserialize(payload)

    assert restored == model
    assert payload["nutrition"]["observed_daily_expenditure_kcal"] is None
    assert payload["recommendations"]["items"] == []


def test_deserialize_does_not_mutate_or_retain_payload_lists():
    serializer = DashboardSerializer()
    payload = serializer.serialize(_full_dashboard())
    before = deepcopy(payload)

    restored = serializer.deserialize(payload)
    payload["health"]["metadata"]["evidence"].append("mutated")

    assert before["health"]["metadata"]["evidence"] == [
        "evidence:b", "evidence:a"
    ]
    assert restored.health.metadata.evidence == ("evidence:b", "evidence:a")
    with pytest.raises(FrozenInstanceError):
        restored.health.metadata.status = DashboardSectionStatus.PARTIAL


def test_deserialize_leaves_original_payload_equal_to_deepcopy():
    payload = DashboardSerializer().serialize(_full_dashboard())
    before = deepcopy(payload)

    DashboardSerializer().deserialize(payload)

    assert payload == before


def test_missing_or_unsupported_contract_version_is_rejected():
    serializer = DashboardSerializer()
    missing = serializer.serialize(_full_dashboard())
    missing.pop("contract_version")
    unsupported = serializer.serialize(_full_dashboard())
    unsupported["contract_version"] = "2.0"

    with pytest.raises(DashboardPayloadError, match="missing required fields"):
        serializer.deserialize(missing)
    with pytest.raises(UnsupportedDashboardContractVersion, match="2.0"):
        serializer.deserialize(unsupported)


def test_serializer_rejects_model_with_unsupported_version():
    model = replace(_full_dashboard(), contract_version="2.0")

    with pytest.raises(UnsupportedDashboardContractVersion, match="2.0"):
        DashboardSerializer().serialize(model)


def test_serializer_rejects_non_json_numeric_value_in_model():
    model = _full_dashboard()
    invalid_health = replace(model.health, hrv_ms=math.nan)

    with pytest.raises(DashboardPayloadError, match="finite number"):
        DashboardSerializer().serialize(replace(model, health=invalid_health))


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda value: value.pop("health"), "missing required fields"),
        (lambda value: value.update({"future": None}), "unknown fields"),
        (
            lambda value: value["health"].update({"future": None}),
            "unknown fields",
        ),
        (
            lambda value: value["health"].pop("hrv_ms"),
            "missing required fields",
        ),
        (
            lambda value: value["recommendations"]["items"][0].pop("id"),
            "missing required fields",
        ),
    ),
)
def test_strict_schema_rejects_missing_and_unknown_fields(mutation, message):
    payload = DashboardSerializer().serialize(_full_dashboard())
    mutation(payload)

    with pytest.raises(DashboardPayloadError, match=message):
        DashboardSerializer().deserialize(payload)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["health"]["metadata"].update({"status": "future"}),
        lambda value: value["training"].update({"workout_goal": "FUTURE"}),
        lambda value: value["training"].update({"decision_action": "future"}),
        lambda value: value["training"].update({"decision_reasons": ["future"]}),
        lambda value: value["goal"].update({"goal_type": "future"}),
        lambda value: value["recommendations"]["items"][0].update(
            {"recommendation_type": "future"}
        ),
        lambda value: value["recommendations"]["items"][0].update(
            {"priority": "future"}
        ),
        lambda value: value["data_quality"].update(
            {"nutrition_status": "future"}
        ),
    ),
)
def test_unknown_enum_values_are_rejected(mutation):
    payload = DashboardSerializer().serialize(_full_dashboard())
    mutation(payload)

    with pytest.raises(DashboardPayloadError, match="unknown enum value"):
        DashboardSerializer().deserialize(payload)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("valid_for_date",), "03-08-2026", "ISO date"),
        (("as_of",), "not-a-datetime", "ISO datetime"),
        (("as_of",), "2026-08-03", "canonical ISO datetime"),
        (("goal", "valid_from"), "2026-99-01", "ISO date"),
        (
            ("recommendations", "items", 0, "as_of"),
            "tomorrow",
            "ISO datetime",
        ),
    ),
)
def test_invalid_dates_and_timestamps_are_rejected(path, value, message):
    payload = DashboardSerializer().serialize(_full_dashboard())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(DashboardPayloadError, match=message):
        DashboardSerializer().deserialize(payload)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value.update({"health": []}),
        lambda value: value["health"].update({"hrv_ms": "42"}),
        lambda value: value["health"]["metadata"].update({"evidence": ()}),
        lambda value: value["recommendations"].update({"items": {}}),
        lambda value: value["recommendations"]["items"].append("item"),
    ),
)
def test_wrong_mapping_list_and_scalar_types_are_rejected(mutation):
    payload = DashboardSerializer().serialize(_full_dashboard())
    mutation(payload)

    with pytest.raises(DashboardPayloadError):
        DashboardSerializer().deserialize(payload)


@pytest.mark.parametrize("invalid", (math.nan, math.inf, -math.inf, True))
@pytest.mark.parametrize(
    "field_path",
    (
        ("health", "hrv_ms"),
        ("health", "metadata", "completeness_score"),
        ("recommendations", "items", 0, "source_confidence"),
    ),
)
def test_non_finite_and_boolean_numeric_values_are_rejected(
    field_path,
    invalid,
):
    payload = DashboardSerializer().serialize(_full_dashboard())
    target = payload
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = invalid

    with pytest.raises(DashboardPayloadError, match="finite number"):
        DashboardSerializer().deserialize(payload)


def test_boolean_integer_value_is_rejected():
    payload = DashboardSerializer().serialize(_full_dashboard())
    payload["health"]["sleep_minutes"] = True

    with pytest.raises(DashboardPayloadError, match="must be an integer"):
        DashboardSerializer().deserialize(payload)


def test_public_serialization_api_exports_only_public_contract_symbols():
    from dashboard.serialization import DashboardSerializer as Implementation

    assert dashboard.DashboardSerializer is Implementation
    assert dashboard.DashboardPayloadError is DashboardPayloadError
    assert (
        dashboard.UnsupportedDashboardContractVersion
        is UnsupportedDashboardContractVersion
    )
    assert not hasattr(dashboard, "_require_exact_keys")


def test_serializer_converts_float_int_fields_to_integers():
    dash = _full_dashboard()
    dash = replace(
        dash,
        health=replace(
            dash.health,
            hrv_ms=62.3,
            steps=12450.0,
            sleep_minutes=480.0,
        ),
    )
    payload = DashboardSerializer().serialize(dash)
    assert payload["health"]["hrv_ms"] == 62.3
    assert payload["health"]["steps"] == 12450
    assert payload["health"]["sleep_minutes"] == 480
    assert isinstance(payload["health"]["hrv_ms"], float)
    assert isinstance(payload["health"]["steps"], int)
    assert isinstance(payload["health"]["sleep_minutes"], int)
