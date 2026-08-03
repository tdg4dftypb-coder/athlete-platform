from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from nutrition import (
    EnergyRequirement,
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionDataStatus,
    NutritionEngine,
    NutritionInput,
)


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6, 0)
ENERGY_DATE = date(2026, 8, 3)
UNAVAILABLE_ASSESSMENT_LIMITATIONS = (
    "missing_estimated_daily_requirement",
    "missing_fresh_body_mass",
    "missing_macro_targets",
    "fat_target_unavailable",
    "missing_training_plan",
    "missing_fueling_plan",
    "electrolyte_target_unavailable",
    "missing_hydration_target",
    "missing_energy_intake",
)


def _input(**changes) -> NutritionInput:
    nutrition_input = NutritionInput(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        resting_energy_kcal=1800.0,
        active_energy_kcal=700.0,
        energy_observed_for_date=ENERGY_DATE,
        evidence=(
            "health_daily:2026-08-03:active_energy",
            "health_daily:2026-08-03:resting_energy",
        ),
    )
    return replace(nutrition_input, **changes)


def test_engine_builds_observed_expenditure_from_daily_energy_only():
    assessment = NutritionEngine().analyze(_input())

    assert assessment.energy_requirement == EnergyRequirement(
        estimated_daily_requirement_kcal=None,
        observed_daily_expenditure_kcal=2500.0,
        resting_energy_kcal=1800.0,
        active_energy_kcal=700.0,
    )
    assert assessment.macro_targets == MacroTargets()
    assert assessment.fueling_plan == FuelingPlan()
    assert assessment.hydration_target == HydrationTarget()


def test_planned_training_data_does_not_increase_observed_expenditure():
    first = NutritionEngine().analyze(
        _input(planned_duration_min=30, planned_target_tss=30.0)
    )
    second = NutritionEngine().analyze(
        _input(planned_duration_min=240, planned_target_tss=300.0)
    )

    assert first.energy_requirement.observed_daily_expenditure_kcal == 2500.0
    assert second.energy_requirement.observed_daily_expenditure_kcal == 2500.0


def test_complete_observed_energy_is_a_partial_assessment():
    assessment = NutritionEngine().analyze(_input())

    assert assessment.data_status is NutritionDataStatus.PARTIAL
    assert assessment.confidence == 0.25
    assert assessment.limitations == UNAVAILABLE_ASSESSMENT_LIMITATIONS
    assert assessment.valid_for_date == VALID_FOR_DATE
    assert assessment.as_of == AS_OF


@pytest.mark.parametrize(
    "changes, missing_limitation",
    (
        (
            {"resting_energy_kcal": None},
            "missing_resting_energy_kcal",
        ),
        (
            {"active_energy_kcal": None},
            "missing_active_energy_kcal",
        ),
        (
            {"energy_observed_for_date": None},
            "missing_energy_observed_for_date",
        ),
    ),
)
def test_partial_energy_data_does_not_create_a_total(
    changes,
    missing_limitation,
):
    assessment = NutritionEngine().analyze(_input(**changes))

    assert assessment.data_status is NutritionDataStatus.PARTIAL
    assert assessment.confidence == 0.125
    assert assessment.energy_requirement.observed_daily_expenditure_kcal is None
    assert missing_limitation in assessment.limitations


def test_missing_energy_data_returns_an_explicit_insufficient_result():
    assessment = NutritionEngine().analyze(
        _input(
            resting_energy_kcal=None,
            active_energy_kcal=None,
            energy_observed_for_date=None,
            evidence=(),
        )
    )

    assert assessment.data_status is NutritionDataStatus.INSUFFICIENT_DATA
    assert assessment.confidence == 0.0
    assert assessment.energy_requirement == EnergyRequirement()
    assert assessment.evidence == ()
    assert assessment.limitations == (
        "missing_resting_energy_kcal",
        "missing_active_energy_kcal",
        "missing_energy_observed_for_date",
    ) + UNAVAILABLE_ASSESSMENT_LIMITATIONS


@pytest.mark.parametrize(
    ("changes", "energy_limitations"),
    (
        (
            {
                "active_energy_kcal": None,
                "energy_observed_for_date": None,
            },
            (
                "missing_active_energy_kcal",
                "missing_energy_observed_for_date",
            ),
        ),
        (
            {
                "resting_energy_kcal": None,
                "energy_observed_for_date": None,
            },
            (
                "missing_resting_energy_kcal",
                "missing_energy_observed_for_date",
            ),
        ),
    ),
)
def test_single_energy_component_without_date_is_partial(
    changes,
    energy_limitations,
):
    assessment = NutritionEngine().analyze(_input(**changes))

    assert assessment.data_status is NutritionDataStatus.PARTIAL
    assert assessment.confidence == 0.125
    assert assessment.energy_requirement.observed_daily_expenditure_kcal is None
    assert assessment.limitations == (
        energy_limitations + UNAVAILABLE_ASSESSMENT_LIMITATIONS
    )


def test_energy_only_inputs_never_return_complete_status():
    assessments = (
        NutritionEngine().analyze(_input()),
        NutritionEngine().analyze(_input(active_energy_kcal=None)),
        NutritionEngine().analyze(
            _input(
                resting_energy_kcal=None,
                active_energy_kcal=None,
                energy_observed_for_date=None,
            )
        ),
    )

    assert all(
        assessment.data_status is not NutritionDataStatus.COMPLETE
        for assessment in assessments
    )


def test_engine_normalizes_evidence_deterministically():
    nutrition_input = _input(
        evidence=(
            "source:b",
            "source:a",
            "source:b",
        )
    )

    assessment = NutritionEngine().analyze(nutrition_input)

    assert assessment.evidence == ("source:a", "source:b")
    assert nutrition_input.evidence == (
        "source:b",
        "source:a",
        "source:b",
    )


def test_evidence_order_does_not_change_the_assessment():
    first = NutritionEngine().analyze(
        _input(evidence=("source:b", "source:a", "source:b"))
    )
    second = NutritionEngine().analyze(
        _input(evidence=("source:a", "source:b"))
    )

    assert first == second


def test_engine_is_stateless_and_deterministic():
    engine = NutritionEngine()
    nutrition_input = _input()

    first = engine.analyze(nutrition_input)
    second = engine.analyze(nutrition_input)

    assert first == second
    assert first is not second


@pytest.mark.parametrize(
    "field_name",
    (
        "body_mass_kg",
        "resting_energy_kcal",
        "active_energy_kcal",
        "recovery_score",
        "planned_duration_min",
        "planned_target_tss",
    ),
)
def test_engine_rejects_negative_numeric_values(field_name):
    with pytest.raises(ValueError, match=field_name):
        NutritionEngine().analyze(_input(**{field_name: -1}))


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("body_mass_kg", float("nan")),
        ("active_energy_kcal", float("inf")),
        ("planned_target_tss", float("-inf")),
    ),
)
def test_engine_rejects_non_finite_numeric_values(field_name, value):
    with pytest.raises(ValueError, match=field_name):
        NutritionEngine().analyze(_input(**{field_name: value}))


@pytest.mark.parametrize(
    "field_name",
    (
        "body_mass_kg",
        "resting_energy_kcal",
        "active_energy_kcal",
        "recovery_score",
        "planned_duration_min",
        "planned_target_tss",
    ),
)
def test_engine_rejects_non_numeric_values(field_name):
    with pytest.raises(TypeError, match=f"{field_name} must be a number"):
        NutritionEngine().analyze(_input(**{field_name: "invalid"}))


@pytest.mark.parametrize(
    "field_name",
    (
        "body_mass_kg",
        "resting_energy_kcal",
        "active_energy_kcal",
        "recovery_score",
        "planned_duration_min",
        "planned_target_tss",
    ),
)
def test_engine_rejects_bool_numeric_values(field_name):
    with pytest.raises(TypeError, match=f"{field_name} must be a number"):
        NutritionEngine().analyze(_input(**{field_name: True}))


def test_engine_rejects_energy_date_without_energy_values():
    with pytest.raises(
        ValueError,
        match="energy_observed_for_date requires an energy value",
    ):
        NutritionEngine().analyze(
            _input(
                resting_energy_kcal=None,
                active_energy_kcal=None,
            )
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        (
            {"energy_observed_for_date": date(2026, 8, 4)},
            "energy_observed_for_date cannot be after valid_for_date",
        ),
        (
            {
                "valid_for_date": date(2026, 8, 5),
                "energy_observed_for_date": date(2026, 8, 4),
            },
            "energy_observed_for_date cannot be after as_of",
        ),
        (
            {
                "body_mass_kg": 80.0,
                "body_mass_observed_at": AS_OF + timedelta(minutes=1),
            },
            "body_mass_observed_at cannot be after as_of",
        ),
        (
            {"body_mass_observed_at": AS_OF},
            "body_mass_observed_at requires body_mass_kg",
        ),
        (
            {"workout_start": datetime(2026, 8, 4, 17, 0)},
            "workout_start must fall on valid_for_date",
        ),
    ),
)
def test_engine_rejects_inconsistent_dates(changes, message):
    with pytest.raises(ValueError, match=message):
        NutritionEngine().analyze(_input(**changes))


def test_engine_rejects_incompatible_timestamp_timezones():
    with pytest.raises(ValueError, match="compatible timezones"):
        NutritionEngine().analyze(
            _input(
                as_of=AS_OF.replace(tzinfo=timezone.utc),
                body_mass_kg=80.0,
                body_mass_observed_at=AS_OF,
            )
        )


def test_engine_rejects_incompatible_workout_start_timezone():
    with pytest.raises(
        ValueError,
        match="workout_start and as_of must use compatible timezones",
    ):
        NutritionEngine().analyze(
            _input(
                workout_start=datetime(
                    2026,
                    8,
                    3,
                    17,
                    0,
                    tzinfo=timezone.utc,
                )
            )
        )


def test_future_planned_workout_on_valid_date_is_allowed():
    assessment = NutritionEngine().analyze(
        _input(workout_start=datetime(2026, 8, 3, 17, 0))
    )

    assert assessment.as_of == AS_OF


def test_energy_stage_does_not_expose_an_energy_balance_without_intake():
    assessment = NutritionEngine().analyze(_input())

    assert not hasattr(assessment, "energy_balance")
    assert not hasattr(assessment.energy_requirement, "energy_balance_kcal")


def test_nutrition_engine_is_publicly_importable():
    assert NutritionEngine.__module__ == "nutrition.engine"
