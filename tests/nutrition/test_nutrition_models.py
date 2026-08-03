from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from nutrition import (
    EnergyRequirement,
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionAssessment,
    NutritionDataStatus,
    NutritionInput,
)


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6, 0)


def _assessment() -> NutritionAssessment:
    return NutritionAssessment(
        energy_requirement=EnergyRequirement(
            estimated_daily_requirement_kcal=2800.0,
            observed_daily_expenditure_kcal=2650.0,
            resting_energy_kcal=1800.0,
            active_energy_kcal=850.0,
        ),
        macro_targets=MacroTargets(
            carbohydrate_g=360.0,
            protein_g=140.0,
            fat_g=80.0,
            carbohydrate_g_per_kg=4.5,
            protein_g_per_kg=1.75,
            fat_g_per_kg=1.0,
        ),
        fueling_plan=FuelingPlan(
            pre_workout_carbohydrate_g=80.0,
            during_workout_carbohydrate_g_per_hour=60.0,
            post_workout_carbohydrate_g=80.0,
            post_workout_protein_g=25.0,
            pre_workout_window_min=120,
            post_workout_window_min=60,
        ),
        hydration_target=HydrationTarget(
            daily_ml=2800.0,
            daily_ml_per_kg=35.0,
            pre_workout_ml=400.0,
            during_workout_ml_per_hour=600.0,
            post_workout_ml=500.0,
        ),
        data_status=NutritionDataStatus.COMPLETE,
        confidence=0.9,
        evidence=("health_daily:2026-08-03", "decision:tempo"),
        limitations=(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


@pytest.mark.parametrize(
    "model, attribute, value",
    (
        (
            NutritionInput(VALID_FOR_DATE, AS_OF),
            "body_mass_kg",
            80.0,
        ),
        (
            EnergyRequirement(),
            "estimated_daily_requirement_kcal",
            2800.0,
        ),
        (MacroTargets(), "protein_g", 140.0),
        (FuelingPlan(), "pre_workout_carbohydrate_g", 80.0),
        (HydrationTarget(), "daily_ml", 2800.0),
        (_assessment(), "confidence", 0.5),
    ),
)
def test_nutrition_models_are_immutable(model, attribute, value):
    with pytest.raises(FrozenInstanceError):
        setattr(model, attribute, value)


def test_public_package_exports_the_v1_domain_contract():
    assert NutritionInput.__module__ == "nutrition.models"
    assert NutritionAssessment.__module__ == "nutrition.models"
    assert EnergyRequirement.__module__ == "nutrition.models"
    assert MacroTargets.__module__ == "nutrition.models"
    assert FuelingPlan.__module__ == "nutrition.models"
    assert HydrationTarget.__module__ == "nutrition.models"
    assert NutritionDataStatus.__module__ == "nutrition.models"


def test_nutrition_input_accepts_partial_normalized_facts():
    nutrition_input = NutritionInput(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        recovery_score=72.0,
        planned_workout_type="tempo",
        planned_duration_min=60,
    )

    assert nutrition_input.body_mass_kg is None
    assert nutrition_input.resting_energy_kcal is None
    assert nutrition_input.active_energy_kcal is None
    assert nutrition_input.workout_start is None
    assert nutrition_input.evidence == ()
    assert nutrition_input.recovery_score == 72.0
    assert nutrition_input.planned_workout_type == "tempo"
    assert nutrition_input.planned_duration_min == 60


def test_assessment_accepts_empty_evidence_and_explicit_limitations():
    assessment = NutritionAssessment(
        energy_requirement=EnergyRequirement(),
        macro_targets=MacroTargets(),
        fueling_plan=FuelingPlan(),
        hydration_target=HydrationTarget(),
        data_status=NutritionDataStatus.INSUFFICIENT_DATA,
        confidence=0.0,
        evidence=(),
        limitations=("missing_body_mass", "missing_energy_data"),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert assessment.evidence == ()
    assert assessment.limitations == (
        "missing_body_mass",
        "missing_energy_data",
    )


def test_nutrition_data_status_matches_the_v1_contract():
    assert tuple(NutritionDataStatus) == (
        NutritionDataStatus.COMPLETE,
        NutritionDataStatus.PARTIAL,
        NutritionDataStatus.INSUFFICIENT_DATA,
    )
    assert tuple(status.value for status in NutritionDataStatus) == (
        "complete",
        "partial",
        "insufficient_data",
    )


def test_construction_is_deterministic_for_identical_domain_data():
    first_input = NutritionInput(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        body_mass_kg=80.0,
        body_mass_observed_at=AS_OF,
        resting_energy_kcal=1800.0,
        active_energy_kcal=850.0,
        energy_observed_for_date=VALID_FOR_DATE,
        recovery_score=85.0,
        planned_sport="cycling",
        planned_workout_type="tempo",
        planned_duration_min=60,
        planned_target_tss=70.0,
        planned_intensity="moderate",
        workout_start=datetime(2026, 8, 3, 17, 0),
        evidence=("health_daily:2026-08-03", "decision:tempo"),
    )
    second_input = NutritionInput(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        body_mass_kg=80.0,
        body_mass_observed_at=AS_OF,
        resting_energy_kcal=1800.0,
        active_energy_kcal=850.0,
        energy_observed_for_date=VALID_FOR_DATE,
        recovery_score=85.0,
        planned_sport="cycling",
        planned_workout_type="tempo",
        planned_duration_min=60,
        planned_target_tss=70.0,
        planned_intensity="moderate",
        workout_start=datetime(2026, 8, 3, 17, 0),
        evidence=("health_daily:2026-08-03", "decision:tempo"),
    )

    assert first_input == second_input
    assert hash(first_input) == hash(second_input)
    assert _assessment() == _assessment()
    assert hash(_assessment()) == hash(_assessment())
