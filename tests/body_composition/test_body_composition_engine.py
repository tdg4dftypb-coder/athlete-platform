from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime, time, timedelta, timezone
import inspect
from math import inf, nan

import pytest

import body_composition.engine as engine_module
from body_composition import (
    BodyCompositionDataStatus,
    BodyCompositionEngine,
    BodyCompositionInput,
    BodyCompositionObservation,
    BodyCompositionProfile,
)


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6)

_METRIC_CASES = (
    ("body_mass_kg", "body_mass", "stale_body_mass"),
    (
        "body_fat_percent",
        "body_fat",
        "stale_body_fat_percentage",
    ),
    ("muscle_mass_kg", "muscle_mass", "stale_muscle_mass"),
    (
        "body_water_percent",
        "body_water",
        "stale_body_water_percentage",
    ),
    ("visceral_fat_rating", "visceral_fat", "stale_visceral_fat"),
    (
        "basal_metabolic_rate_kcal",
        "basal_metabolic_rate",
        "stale_basal_metabolic_rate",
    ),
    (
        "waist_circumference_cm",
        "waist_circumference",
        "stale_waist_circumference",
    ),
)


def _observation(
    observed_for_date: date = VALID_FOR_DATE,
    **changes,
) -> BodyCompositionObservation:
    values = {
        "body_mass_kg": None,
        "body_fat_percent": None,
        "muscle_mass_kg": None,
        "body_water_percent": None,
        "visceral_fat_rating": None,
        "basal_metabolic_rate_kcal": None,
        "waist_circumference_cm": None,
        "evidence": (),
    }
    values.update(changes)
    return BodyCompositionObservation(
        observed_for_date=observed_for_date,
        **values,
    )


def _input(
    observations: tuple[BodyCompositionObservation, ...],
    *,
    valid_for_date: date = VALID_FOR_DATE,
    as_of: datetime = AS_OF,
    evidence: tuple[str, ...] = (),
) -> BodyCompositionInput:
    return BodyCompositionInput(
        observations=observations,
        valid_for_date=valid_for_date,
        as_of=as_of,
        evidence=evidence,
    )


def _full_observation(
    observed_for_date: date = VALID_FOR_DATE,
) -> BodyCompositionObservation:
    return _observation(
        observed_for_date,
        body_mass_kg=80.0,
        body_fat_percent=15.0,
        muscle_mass_kg=38.0,
        body_water_percent=58.0,
        visceral_fat_rating=7.0,
        basal_metabolic_rate_kcal=1800.0,
        waist_circumference_cm=82.0,
        evidence=("body_source:2026-08-03",),
    )


def test_engine_builds_a_full_current_profile_without_a_trend():
    result = BodyCompositionEngine().analyze(_input((_full_observation(),)))

    assert result.profile.body_mass.value == 80.0
    assert result.profile.body_fat.value == 15.0
    assert result.profile.muscle_mass.value == 38.0
    assert result.profile.body_water.value == 58.0
    assert result.profile.visceral_fat.value == 7.0
    assert result.profile.basal_metabolic_rate.value == 1800.0
    assert result.profile.waist_circumference.value == 82.0
    assert result.body_mass_trend is None
    assert result.confidence == 0.75
    assert result.data_status is BodyCompositionDataStatus.PARTIAL
    assert result.limitations == ("insufficient_body_mass_history",)


def test_engine_supports_only_body_mass():
    result = BodyCompositionEngine().analyze(
        _input((_observation(body_mass_kg=80.0),))
    )

    assert result.profile.body_mass.value == 80.0
    assert result.profile.body_fat is None
    assert result.profile.muscle_mass is None
    assert result.confidence == 0.25
    assert result.data_status is BodyCompositionDataStatus.PARTIAL


def test_engine_returns_insufficient_assessment_without_observations():
    result = BodyCompositionEngine().analyze(_input(()))

    assert result.profile == BodyCompositionProfile()
    assert result.body_mass_trend is None
    assert result.confidence == 0.0
    assert result.data_status is BodyCompositionDataStatus.INSUFFICIENT_DATA
    assert result.limitations == (
        "missing_body_mass",
        "missing_body_fat_percentage",
        "missing_muscle_mass",
        "missing_body_water_percentage",
        "missing_visceral_fat",
        "missing_basal_metabolic_rate",
        "missing_waist_circumference",
        "insufficient_body_mass_history",
    )


def test_metrics_keep_their_distinct_observation_dates():
    observations = (
        _observation(date(2026, 8, 3), body_mass_kg=80.0),
        _observation(date(2026, 8, 2), body_fat_percent=15.0),
        _observation(date(2026, 8, 1), muscle_mass_kg=38.0),
    )

    profile = BodyCompositionEngine().analyze(_input(observations)).profile

    assert profile.body_mass.observed_at == datetime(2026, 8, 3)
    assert profile.body_fat.observed_at == datetime(2026, 8, 2)
    assert profile.muscle_mass.observed_at == datetime(2026, 8, 1)


def test_latest_selection_does_not_depend_on_observation_order():
    observations = (
        _observation(date(2026, 8, 1), body_mass_kg=81.0),
        _observation(date(2026, 8, 3), body_mass_kg=80.0),
        _observation(date(2026, 8, 2), body_mass_kg=80.5),
    )
    engine = BodyCompositionEngine()

    first = engine.analyze(_input(observations))
    second = engine.analyze(_input(tuple(reversed(observations))))

    assert first == second
    assert first.profile.body_mass.value == 80.0


def test_measurement_exactly_30_days_old_is_fresh():
    day = VALID_FOR_DATE - timedelta(days=30)

    result = BodyCompositionEngine().analyze(
        _input((_observation(day, body_mass_kg=80.0),))
    )

    assert result.profile.body_mass is not None
    assert "stale_body_mass" not in result.limitations


def test_measurement_31_days_old_is_stale():
    day = VALID_FOR_DATE - timedelta(days=31)

    result = BodyCompositionEngine().analyze(
        _input((_observation(day, body_mass_kg=80.0),))
    )

    assert result.profile.body_mass is None
    assert result.confidence == 0.0
    assert result.data_status is BodyCompositionDataStatus.INSUFFICIENT_DATA
    assert "stale_body_mass" in result.limitations
    assert "missing_body_mass" not in result.limitations


def test_stale_measurement_keeps_source_evidence():
    day = VALID_FOR_DATE - timedelta(days=31)
    observation = _observation(
        day,
        body_mass_kg=80.0,
        evidence=("body_source:2026-07-03",),
    )

    result = BodyCompositionEngine().analyze(_input((observation,)))

    assert result.profile.body_mass is None
    assert result.evidence == ("body_source:2026-07-03",)


@pytest.mark.parametrize(
    ("input_field", "profile_field", "stale_limitation"),
    _METRIC_CASES,
)
def test_each_metric_uses_the_freshness_policy(
    input_field,
    profile_field,
    stale_limitation,
):
    observation = _observation(
        VALID_FOR_DATE - timedelta(days=31),
        **{input_field: 10.0},
    )

    result = BodyCompositionEngine().analyze(_input((observation,)))

    assert getattr(result.profile, profile_field) is None
    assert stale_limitation in result.limitations


def test_observation_after_valid_for_date_is_rejected():
    observation = _observation(
        VALID_FOR_DATE + timedelta(days=1),
        body_mass_kg=80.0,
    )

    with pytest.raises(ValueError, match="after valid_for_date"):
        BodyCompositionEngine().analyze(_input((observation,)))


def test_valid_for_date_after_as_of_is_rejected():
    as_of = datetime(2026, 8, 2, 23)

    with pytest.raises(ValueError, match="valid_for_date cannot be after as_of"):
        BodyCompositionEngine().analyze(
            _input(
                (_observation(body_mass_kg=80.0),),
                as_of=as_of,
            )
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("body_mass_kg", 0.0),
        ("body_mass_kg", -1.0),
        ("muscle_mass_kg", 0.0),
        ("visceral_fat_rating", 0.0),
        ("basal_metabolic_rate_kcal", 0.0),
        ("waist_circumference_cm", 0.0),
    ),
)
def test_positive_metrics_reject_zero_and_negative_values(field_name, value):
    with pytest.raises(ValueError, match="must be positive"):
        BodyCompositionEngine().analyze(
            _input((_observation(**{field_name: value}),))
        )


@pytest.mark.parametrize("value", (nan, inf, -inf))
def test_non_finite_values_are_rejected(value):
    with pytest.raises(ValueError, match="must be finite"):
        BodyCompositionEngine().analyze(
            _input((_observation(body_mass_kg=value),))
        )


@pytest.mark.parametrize("value", (True, False, "80", object()))
def test_bool_and_non_numeric_values_are_rejected(value):
    with pytest.raises(TypeError, match="must be a number"):
        BodyCompositionEngine().analyze(
            _input((_observation(body_mass_kg=value),))
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("body_fat_percent", -0.1),
        ("body_fat_percent", 100.1),
        ("body_water_percent", -0.1),
        ("body_water_percent", 100.1),
    ),
)
def test_percentages_outside_the_inclusive_range_are_rejected(
    field_name,
    value,
):
    with pytest.raises(ValueError, match="between 0 and 100"):
        BodyCompositionEngine().analyze(
            _input((_observation(**{field_name: value}),))
        )


@pytest.mark.parametrize("value", (0.0, 100.0))
def test_percentage_boundaries_are_accepted(value):
    result = BodyCompositionEngine().analyze(
        _input((_observation(body_fat_percent=value),))
    )

    assert result.profile.body_fat.value == value


def test_empty_observation_is_rejected():
    with pytest.raises(ValueError, match="at least one metric"):
        BodyCompositionEngine().analyze(_input((_observation(),)))


def test_conflicting_duplicates_are_rejected_per_metric():
    observations = (
        _observation(body_mass_kg=80.0, body_fat_percent=15.0),
        _observation(body_mass_kg=81.0, body_fat_percent=15.0),
    )

    with pytest.raises(ValueError, match="conflicting body_mass_kg"):
        BodyCompositionEngine().analyze(_input(observations))


def test_identical_duplicates_are_normalized():
    observations = (
        _observation(body_mass_kg=80.0, evidence=("source:b",)),
        _observation(body_mass_kg=80.0, evidence=("source:a",)),
    )

    result = BodyCompositionEngine().analyze(_input(observations))

    assert result.profile.body_mass.value == 80.0
    assert result.evidence == ("source:a", "source:b")


def test_naive_and_aware_inputs_produce_matching_measurement_timezones():
    naive = BodyCompositionEngine().analyze(
        _input((_observation(body_mass_kg=80.0),))
    )
    aware_as_of = datetime(2026, 8, 3, 6, tzinfo=timezone.utc)
    aware = BodyCompositionEngine().analyze(
        _input(
            (_observation(body_mass_kg=80.0),),
            as_of=aware_as_of,
        )
    )

    assert naive.profile.body_mass.observed_at.tzinfo is None
    assert aware.profile.body_mass.observed_at.tzinfo is timezone.utc


def test_mixed_naive_and_aware_temporal_contract_is_rejected(monkeypatch):
    monkeypatch.setattr(
        BodyCompositionEngine,
        "_at_start_of_day",
        staticmethod(lambda day, as_of: datetime.combine(day, time.min)),
    )
    aware_as_of = datetime(2026, 8, 3, 6, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="compatible timezones"):
        BodyCompositionEngine().analyze(
            _input(
                (_observation(body_mass_kg=80.0),),
                as_of=aware_as_of,
            )
        )


@pytest.mark.parametrize(
    ("observation", "expected_confidence", "expected_status"),
    (
        (
            None,
            0.0,
            BodyCompositionDataStatus.INSUFFICIENT_DATA,
        ),
        (
            _observation(body_mass_kg=80.0),
            0.25,
            BodyCompositionDataStatus.PARTIAL,
        ),
        (
            _observation(body_mass_kg=80.0, body_fat_percent=15.0),
            0.5,
            BodyCompositionDataStatus.PARTIAL,
        ),
        (
            _observation(
                body_mass_kg=80.0,
                body_fat_percent=15.0,
                muscle_mass_kg=38.0,
            ),
            0.75,
            BodyCompositionDataStatus.PARTIAL,
        ),
    ),
)
def test_confidence_and_status_cover_stage_8_3_completeness_policy(
    observation,
    expected_confidence,
    expected_status,
):
    observations = () if observation is None else (observation,)

    result = BodyCompositionEngine().analyze(_input(observations))

    assert result.confidence == expected_confidence
    assert result.data_status is expected_status
    assert result.data_status is not BodyCompositionDataStatus.COMPLETE
    assert result.body_mass_trend is None


def test_evidence_and_temporal_contract_are_preserved_deterministically():
    observations = (
        _observation(body_mass_kg=80.0, evidence=("source:c", "source:a")),
        _observation(body_fat_percent=15.0, evidence=("source:b",)),
    )
    body_input = _input(
        observations,
        evidence=("source:b", "input:a"),
    )

    result = BodyCompositionEngine().analyze(body_input)

    assert result.evidence == (
        "input:a",
        "source:a",
        "source:b",
        "source:c",
    )
    assert result.valid_for_date == VALID_FOR_DATE
    assert result.as_of == AS_OF


def test_engine_is_deterministic_and_does_not_mutate_input():
    observations = (
        _observation(date(2026, 8, 2), body_mass_kg=81.0),
        _observation(
            date(2026, 8, 3),
            body_mass_kg=80.0,
            body_fat_percent=15.0,
            evidence=("source:b", "source:a"),
        ),
    )
    body_input = _input(
        observations,
        evidence=("input:b", "input:a"),
    )
    original = deepcopy(body_input)
    engine = BodyCompositionEngine()

    first = engine.analyze(body_input)
    second = engine.analyze(body_input)
    reversed_result = engine.analyze(
        _input(
            tuple(reversed(observations)),
            evidence=tuple(reversed(body_input.evidence)),
        )
    )

    assert first == second == reversed_result
    assert body_input == original
    with pytest.raises(FrozenInstanceError):
        first.confidence = 0.0


def test_engine_is_public_and_has_no_forbidden_architecture_dependencies():
    from body_composition import BodyCompositionEngine as PublicEngine

    source = inspect.getsource(engine_module).lower()

    assert PublicEngine is BodyCompositionEngine
    for forbidden in (
        "application",
        "recommendation",
        "morningcoach",
        "repository",
        "duckdb",
        "datetime.now",
        "date.today",
        "random",
        "uuid",
        "open(",
    ):
        assert forbidden not in source
