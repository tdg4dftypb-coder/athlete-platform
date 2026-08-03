from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta

import pytest

from nutrition import (
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionDataStatus,
    NutritionEngine,
    NutritionInput,
)


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6, 0)


def _input(**changes) -> NutritionInput:
    nutrition_input = NutritionInput(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        body_mass_kg=80.0,
        body_mass_observed_at=AS_OF - timedelta(days=10),
        resting_energy_kcal=1800.0,
        active_energy_kcal=700.0,
        energy_observed_for_date=VALID_FOR_DATE,
        planned_workout_type="endurance",
        planned_duration_min=90,
        planned_target_tss=60.0,
        evidence=("source:b", "source:a"),
    )
    return replace(nutrition_input, **changes)


@pytest.mark.parametrize(
    ("age", "is_fresh"),
    (
        (timedelta(days=10), True),
        (timedelta(days=30), True),
        (timedelta(days=31), False),
    ),
)
def test_body_mass_freshness_v1_has_an_inclusive_30_day_boundary(
    age,
    is_fresh,
):
    assessment = NutritionEngine().analyze(
        _input(body_mass_observed_at=AS_OF - age)
    )

    assert (assessment.macro_targets.protein_g is not None) is is_fresh
    assert (assessment.hydration_target.daily_ml is not None) is is_fresh
    assert (
        "missing_fresh_body_mass" in assessment.limitations
    ) is not is_fresh


@pytest.mark.parametrize(
    "changes",
    (
        {"body_mass_kg": None, "body_mass_observed_at": None},
        {"body_mass_observed_at": None},
        {"body_mass_observed_at": AS_OF - timedelta(days=31)},
    ),
)
def test_missing_or_stale_body_mass_never_creates_mass_based_targets(changes):
    assessment = NutritionEngine().analyze(_input(**changes))

    assert assessment.macro_targets == MacroTargets()
    assert assessment.hydration_target.daily_ml is None
    assert assessment.hydration_target.daily_ml_per_kg is None
    assert assessment.hydration_target.pre_workout_ml is None
    assert assessment.fueling_plan.post_workout_carbohydrate_g is None
    assert assessment.fueling_plan.post_workout_protein_g is None
    assert "missing_fresh_body_mass" in assessment.limitations


@pytest.mark.parametrize(
    "value",
    (-1.0, 0.0, float("nan"), float("inf"), float("-inf")),
)
def test_invalid_body_mass_is_rejected(value):
    with pytest.raises(ValueError, match="body_mass_kg"):
        NutritionEngine().analyze(_input(body_mass_kg=value))


@pytest.mark.parametrize(
    ("workout_type", "duration", "expected_carbohydrate_per_kg"),
    (
        ("rest", None, 3.0),
        ("recovery", 45, 3.5),
        ("endurance", 90, 4.5),
        ("tempo", 60, 5.0),
        ("threshold", 60, 6.0),
        ("vo2", 60, 6.0),
        ("endurance", 45, 3.5),
        ("endurance", 120, 6.0),
    ),
)
def test_macro_carbohydrates_follow_training_demand(
    workout_type,
    duration,
    expected_carbohydrate_per_kg,
):
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type=workout_type,
            planned_duration_min=duration,
            planned_target_tss=None,
        )
    )

    targets = assessment.macro_targets
    assert targets.carbohydrate_g_per_kg == expected_carbohydrate_per_kg
    assert targets.carbohydrate_g == 80.0 * expected_carbohydrate_per_kg
    assert targets.protein_g_per_kg == 1.6
    assert targets.protein_g == 128.0
    assert targets.fat_g is None
    assert targets.fat_g_per_kg is None
    assert "fat_target_unavailable" in assessment.limitations


def test_macro_policy_has_explicit_tss_boundary():
    below = NutritionEngine().analyze(
        _input(planned_target_tss=89.9)
    )
    at_boundary = NutritionEngine().analyze(
        _input(planned_target_tss=90.0)
    )

    assert below.macro_targets.carbohydrate_g_per_kg == 4.5
    assert at_boundary.macro_targets.carbohydrate_g_per_kg == 6.0


def test_no_training_data_returns_no_fueling_plan():
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type=None,
            planned_duration_min=None,
            planned_target_tss=None,
            planned_intensity=None,
        )
    )

    assert assessment.fueling_plan == FuelingPlan()
    assert "missing_training_plan" in assessment.limitations
    assert "missing_fueling_plan" in assessment.limitations


def test_rest_has_an_explicit_not_applicable_fueling_plan():
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type="rest",
            planned_duration_min=None,
            planned_target_tss=None,
        )
    )

    assert assessment.fueling_plan == FuelingPlan()
    assert "missing_fueling_plan" not in assessment.limitations


def test_short_light_training_uses_zero_during_workout_carbohydrate():
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type="recovery",
            planned_duration_min=45,
            planned_target_tss=25.0,
        )
    )

    assert assessment.fueling_plan == FuelingPlan(
        pre_workout_carbohydrate_g=20.0,
        during_workout_carbohydrate_g_per_hour=0.0,
        post_workout_carbohydrate_g=40.0,
        post_workout_protein_g=24.0,
        pre_workout_window_min=120,
        post_workout_window_min=60,
    )


@pytest.mark.parametrize("workout_type", ("threshold", "vo2"))
def test_intense_training_uses_high_demand_fueling(workout_type):
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type=workout_type,
            planned_duration_min=60,
            planned_target_tss=80.0,
        )
    )

    assert assessment.fueling_plan.pre_workout_carbohydrate_g == 75.0
    assert (
        assessment.fueling_plan.during_workout_carbohydrate_g_per_hour
        == 60.0
    )
    assert assessment.fueling_plan.post_workout_carbohydrate_g == 80.0


def test_long_endurance_uses_high_demand_fueling():
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type="endurance",
            planned_duration_min=180,
            planned_target_tss=80.0,
        )
    )

    assert assessment.fueling_plan.pre_workout_carbohydrate_g == 75.0
    assert (
        assessment.fueling_plan.during_workout_carbohydrate_g_per_hour
        == 60.0
    )


@pytest.mark.parametrize(
    ("duration", "expected_rate"),
    (
        (45, 0.0),
        (46, 30.0),
        (119, 30.0),
        (120, 60.0),
    ),
)
def test_fueling_duration_boundaries_are_explicit(duration, expected_rate):
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type="endurance",
            planned_duration_min=duration,
            planned_target_tss=60.0,
        )
    )

    assert (
        assessment.fueling_plan.during_workout_carbohydrate_g_per_hour
        == expected_rate
    )


def test_fueling_uses_relative_windows_without_workout_start():
    without_start = NutritionEngine().analyze(_input(workout_start=None))
    with_start = NutritionEngine().analyze(
        _input(workout_start=datetime(2026, 8, 3, 17, 0))
    )

    assert without_start.fueling_plan == with_start.fueling_plan
    assert without_start.fueling_plan.pre_workout_window_min == 120
    assert without_start.fueling_plan.post_workout_window_min == 60


def test_fueling_without_duration_is_partial_and_does_not_invent_a_rate():
    assessment = NutritionEngine().analyze(
        _input(
            planned_workout_type="tempo",
            planned_duration_min=None,
            planned_target_tss=None,
        )
    )

    assert assessment.fueling_plan.pre_workout_carbohydrate_g == 60.0
    assert assessment.fueling_plan.during_workout_carbohydrate_g_per_hour is None
    assert "missing_planned_duration" in assessment.limitations
    assert "missing_fueling_plan" in assessment.limitations


def test_hydration_policy_uses_fresh_body_mass_and_fixed_workout_rate():
    assessment = NutritionEngine().analyze(_input())

    assert assessment.hydration_target == HydrationTarget(
        daily_ml=2800.0,
        daily_ml_per_kg=35.0,
        pre_workout_ml=400.0,
        during_workout_ml_per_hour=500.0,
        post_workout_ml=None,
    )
    assert "missing_sweat_rate" in assessment.limitations
    assert "missing_environment_data" in assessment.limitations
    assert "electrolyte_target_unavailable" in assessment.limitations


def test_stale_mass_keeps_only_non_personalized_workout_hydration():
    assessment = NutritionEngine().analyze(
        _input(body_mass_observed_at=AS_OF - timedelta(days=31))
    )

    assert assessment.hydration_target == HydrationTarget(
        during_workout_ml_per_hour=500.0,
    )
    assert "missing_fresh_body_mass" in assessment.limitations
    assert "missing_hydration_target" in assessment.limitations
    assert "missing_sweat_rate" in assessment.limitations
    assert "missing_environment_data" in assessment.limitations
    assert "electrolyte_target_unavailable" in assessment.limitations


def test_complete_assessment_requires_all_four_mvp_sections():
    assessment = NutritionEngine().analyze(_input())

    assert assessment.data_status is NutritionDataStatus.COMPLETE
    assert assessment.confidence == 1.0
    assert "missing_macro_targets" not in assessment.limitations
    assert "missing_fueling_plan" not in assessment.limitations
    assert "missing_hydration_target" not in assessment.limitations
    assert assessment.limitations == (
        "missing_estimated_daily_requirement",
        "fat_target_unavailable",
        "missing_sweat_rate",
        "missing_environment_data",
        "electrolyte_target_unavailable",
        "missing_energy_intake",
    )


def test_partial_assessment_confidence_sums_section_completeness():
    assessment = NutritionEngine().analyze(
        _input(body_mass_observed_at=AS_OF - timedelta(days=31))
    )

    assert assessment.data_status is NutritionDataStatus.PARTIAL
    assert assessment.confidence == 0.625


def test_no_usable_sections_is_insufficient_data():
    assessment = NutritionEngine().analyze(
        NutritionInput(valid_for_date=VALID_FOR_DATE, as_of=AS_OF)
    )

    assert assessment.data_status is NutritionDataStatus.INSUFFICIENT_DATA
    assert assessment.confidence == 0.0


def test_policy_output_is_immutable_and_does_not_mutate_input():
    nutrition_input = _input()
    assessment = NutritionEngine().analyze(nutrition_input)

    with pytest.raises(FrozenInstanceError):
        assessment.confidence = 0.0
    assert nutrition_input == _input()


def test_policy_output_is_deterministic_and_evidence_order_independent():
    engine = NutritionEngine()
    first = engine.analyze(_input(evidence=("source:b", "source:a", "source:b")))
    second = engine.analyze(_input(evidence=("source:a", "source:b")))

    assert first == second
    assert first.evidence == ("source:a", "source:b")
    assert len(first.limitations) == len(set(first.limitations))
