from datetime import date, datetime, timedelta

import pytest

from application import NutritionInputBuilder
from core.models import HealthDaily
from decision.models import DecisionResult
from decision.sports import Sport
from nutrition import NutritionEngine
from workout.enums import WorkoutType


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6, 0)


def _decision() -> DecisionResult:
    return DecisionResult(
        sport=Sport.CYCLING,
        recommendation=WorkoutType.ENDURANCE,
        duration=90,
        target_tss=60.0,
        intensity="Z2",
        reasons=[],
    )


def _build(
    health_history: tuple[HealthDaily, ...],
    **changes,
):
    parameters = {
        "valid_for_date": VALID_FOR_DATE,
        "as_of": AS_OF,
        "health_history": health_history,
        "recovery_score": 82.0,
        "workout_start": None,
        "evidence": ("source:b", "source:a", "source:b"),
    }
    parameters.update(changes)
    return NutritionInputBuilder().build(_decision(), **parameters)


def test_builder_maps_complete_health_energy_and_canonical_decision():
    health = HealthDaily(
        date=VALID_FOR_DATE,
        weight=80.0,
        resting_energy=1800,
        active_energy=700,
    )

    result = _build((health,))

    assert result.valid_for_date == VALID_FOR_DATE
    assert result.as_of == AS_OF
    assert result.body_mass_kg == 80.0
    assert result.body_mass_observed_at == datetime(2026, 8, 3)
    assert result.resting_energy_kcal == 1800.0
    assert result.active_energy_kcal == 700.0
    assert result.energy_observed_for_date == VALID_FOR_DATE
    assert result.recovery_score == 82.0
    assert result.planned_sport == "cycling"
    assert result.planned_workout_type == "endurance"
    assert result.planned_duration_min == 90
    assert result.planned_target_tss == 60.0
    assert result.planned_intensity == "Z2"
    assert result.workout_start is None


@pytest.mark.parametrize(
    ("resting", "active", "expected_date"),
    (
        (None, 700, VALID_FOR_DATE),
        (1800, None, VALID_FOR_DATE),
        (None, None, None),
    ),
)
def test_builder_preserves_missing_energy_without_guessing(
    resting,
    active,
    expected_date,
):
    result = _build(
        (
            HealthDaily(
                date=VALID_FOR_DATE,
                resting_energy=resting,
                active_energy=active,
            ),
        )
    )

    assert result.resting_energy_kcal == resting
    assert result.active_energy_kcal == active
    assert result.energy_observed_for_date == expected_date


@pytest.mark.parametrize(
    ("age_days", "is_fresh"),
    ((10, True), (31, False)),
)
def test_builder_preserves_body_mass_age_for_domain_freshness_policy(
    age_days,
    is_fresh,
):
    body_mass_day = HealthDaily(
        date=VALID_FOR_DATE - timedelta(days=age_days),
        weight=80.0,
    )
    current_day = HealthDaily(
        date=VALID_FOR_DATE,
        resting_energy=1800,
        active_energy=700,
    )

    nutrition_input = _build((body_mass_day, current_day))
    assessment = NutritionEngine().analyze(nutrition_input)

    assert nutrition_input.body_mass_kg == 80.0
    assert nutrition_input.body_mass_observed_at == datetime.combine(
        body_mass_day.date,
        datetime.min.time(),
    )
    assert (
        assessment.macro_targets.protein_g is not None
    ) is is_fresh


def test_builder_keeps_body_mass_missing_when_history_has_no_measurement():
    result = _build((HealthDaily(date=VALID_FOR_DATE),))

    assert result.body_mass_kg is None
    assert result.body_mass_observed_at is None


def test_builder_does_not_create_a_workout_start():
    result = _build((HealthDaily(date=VALID_FOR_DATE),))

    assert result.workout_start is None


def test_builder_preserves_explicit_workout_start():
    workout_start = datetime(2026, 8, 3, 17, 0)

    result = _build(
        (HealthDaily(date=VALID_FOR_DATE),),
        workout_start=workout_start,
    )

    assert result.workout_start is workout_start


def test_builder_preserves_missing_plan_facts_without_guessing():
    decision = _decision()
    decision.duration = None
    decision.target_tss = None
    decision.intensity = None

    result = NutritionInputBuilder().build(
        decision,
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert result.planned_duration_min is None
    assert result.planned_target_tss is None
    assert result.planned_intensity is None


def test_builder_normalizes_evidence_deterministically():
    health = HealthDaily(date=VALID_FOR_DATE, weight=80.0)

    first = _build((health,))
    second = _build(
        (health,),
        evidence=("source:a", "source:b"),
    )

    assert first == second
    assert first.evidence == (
        "body_mass:2026-08-03",
        "decision:endurance",
        "health_daily:2026-08-03",
        "source:a",
        "source:b",
    )
