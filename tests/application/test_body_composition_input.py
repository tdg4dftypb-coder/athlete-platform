from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from application import BodyCompositionInputBuilder
from body_composition import BodyCompositionEngine
from core.models import HealthDaily


AS_OF = datetime(2026, 8, 3, 7, 30)


def test_builder_maps_a_single_body_mass_observation_in_kg():
    result = BodyCompositionInputBuilder().build(
        health_history=(HealthDaily(date(2026, 8, 2), weight=80.5),),
        as_of=AS_OF,
    )

    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.observed_for_date == date(2026, 8, 2)
    assert observation.body_mass_kg == 80.5
    assert observation.body_fat_percent is None
    assert observation.muscle_mass_kg is None
    assert observation.body_water_percent is None
    assert observation.visceral_fat_rating is None
    assert observation.basal_metabolic_rate_kcal is None
    assert observation.waist_circumference_cm is None


def test_builder_maps_multiple_measurements_and_ignores_days_without_weight():
    history = (
        HealthDaily(date(2026, 8, 1), weight=81.0),
        HealthDaily(date(2026, 8, 2), weight=None),
        HealthDaily(date(2026, 8, 3), weight=80.5),
    )

    result = BodyCompositionInputBuilder().build(
        health_history=history,
        as_of=AS_OF,
    )

    assert tuple(
        (item.observed_for_date, item.body_mass_kg)
        for item in result.observations
    ) == (
        (date(2026, 8, 1), 81.0),
        (date(2026, 8, 3), 80.5),
    )


@pytest.mark.parametrize(
    "history",
    (
        (),
        (HealthDaily(date(2026, 8, 3)),),
    ),
)
def test_builder_accepts_empty_or_weightless_history(history):
    result = BodyCompositionInputBuilder().build(
        health_history=history,
        as_of=AS_OF,
    )

    assert result.observations == ()
    assert result.evidence == ()


def test_builder_excludes_records_after_the_valid_date():
    result = BodyCompositionInputBuilder().build(
        health_history=(
            HealthDaily(date(2026, 8, 3), weight=80.0),
            HealthDaily(date(2026, 8, 4), weight=79.5),
        ),
        as_of=AS_OF,
    )

    assert tuple(
        item.observed_for_date for item in result.observations
    ) == (date(2026, 8, 3),)


def test_builder_produces_stable_deduplicated_evidence_and_temporal_fields():
    result = BodyCompositionInputBuilder().build(
        health_history=(
            HealthDaily(date(2026, 8, 2), weight=80.5),
            HealthDaily(date(2026, 8, 2), weight=80.5),
            HealthDaily(date(2026, 8, 3), weight=80.0),
        ),
        as_of=AS_OF,
    )

    assert result.valid_for_date == date(2026, 8, 3)
    assert result.as_of is AS_OF
    assert result.evidence == (
        "body_mass:2026-08-02",
        "body_mass:2026-08-03",
    )
    assert tuple(item.evidence for item in result.observations) == (
        ("body_mass:2026-08-02",),
        ("body_mass:2026-08-03",),
    )


def test_builder_is_independent_of_history_order_and_deduplicates_exact_records():
    history = (
        HealthDaily(date(2026, 8, 3), weight=80.0),
        HealthDaily(date(2026, 8, 1), weight=81.0),
        HealthDaily(date(2026, 8, 1), weight=81.0),
        HealthDaily(date(2026, 8, 2), weight=80.5),
    )
    builder = BodyCompositionInputBuilder()

    forward = builder.build(health_history=history, as_of=AS_OF)
    reversed_result = builder.build(
        health_history=tuple(reversed(history)),
        as_of=AS_OF,
    )

    assert forward == reversed_result
    assert len(forward.observations) == 3


def test_builder_keeps_same_day_conflicts_visible_to_the_domain_engine():
    result = BodyCompositionInputBuilder().build(
        health_history=(
            HealthDaily(date(2026, 8, 3), weight=80.0),
            HealthDaily(date(2026, 8, 3), weight=81.0),
        ),
        as_of=AS_OF,
    )

    assert tuple(item.body_mass_kg for item in result.observations) == (
        80.0,
        81.0,
    )
    with pytest.raises(ValueError, match="conflicting body_mass_kg"):
        BodyCompositionEngine().analyze(result)


def test_builder_does_not_mutate_health_history_and_is_deterministic():
    history = (
        HealthDaily(date(2026, 8, 2), weight=80.5),
        HealthDaily(date(2026, 8, 3), weight=80.0),
    )
    original = deepcopy(history)
    builder = BodyCompositionInputBuilder()

    first = builder.build(health_history=history, as_of=AS_OF)
    second = builder.build(health_history=history, as_of=AS_OF)

    assert first == second
    assert history == original
    with pytest.raises(FrozenInstanceError):
        first.observations = ()


def test_application_publicly_exports_body_composition_input_builder():
    from application import BodyCompositionInputBuilder as PublicBuilder

    assert PublicBuilder is BodyCompositionInputBuilder
