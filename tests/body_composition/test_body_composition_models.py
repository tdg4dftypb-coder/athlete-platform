from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionInput,
    BodyCompositionObservation,
    BodyCompositionProfile,
    BodyMassTrend,
    BodyMeasurement,
)


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6)


def _observation() -> BodyCompositionObservation:
    return BodyCompositionObservation(
        observed_for_date=VALID_FOR_DATE,
        body_mass_kg=80.0,
        body_fat_percent=15.0,
        muscle_mass_kg=38.0,
        body_water_percent=58.0,
        visceral_fat_rating=7.0,
        basal_metabolic_rate_kcal=1800.0,
        waist_circumference_cm=82.0,
        evidence=("body_source:2026-08-03",),
    )


def _complete_assessment() -> BodyCompositionAssessment:
    body_mass = BodyMeasurement(80.0, AS_OF)
    baseline = BodyMeasurement(81.0, datetime(2026, 7, 27, 6))
    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(
            body_mass=body_mass,
            body_fat=BodyMeasurement(15.0, datetime(2026, 8, 2, 7)),
            muscle_mass=BodyMeasurement(38.0, datetime(2026, 8, 1, 7)),
            body_water=BodyMeasurement(58.0, datetime(2026, 7, 31, 7)),
            visceral_fat=BodyMeasurement(7.0, datetime(2026, 7, 30, 7)),
            basal_metabolic_rate=BodyMeasurement(
                1800.0,
                datetime(2026, 7, 29, 7),
            ),
            waist_circumference=BodyMeasurement(
                82.0,
                datetime(2026, 7, 28, 7),
            ),
        ),
        body_mass_trend=BodyMassTrend(
            current=body_mass,
            baseline=baseline,
            period_days=7,
            absolute_change_kg=-1.0,
            percentage_change=-1.234567,
        ),
        data_status=BodyCompositionDataStatus.COMPLETE,
        confidence=1.0,
        evidence=("body_source:2026-08-03",),
        limitations=(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


@pytest.mark.parametrize(
    ("model", "attribute", "replacement"),
    (
        (_observation(), "body_mass_kg", 79.0),
        (BodyMeasurement(80.0, AS_OF), "value", 79.0),
        (BodyCompositionProfile(), "body_mass", BodyMeasurement(80.0, AS_OF)),
        (
            BodyMassTrend(
                current=BodyMeasurement(80.0, AS_OF),
                baseline=BodyMeasurement(81.0, datetime(2026, 7, 27, 6)),
                period_days=7,
                absolute_change_kg=-1.0,
                percentage_change=-1.234567,
            ),
            "period_days",
            14,
        ),
        (
            BodyCompositionInput((), VALID_FOR_DATE, AS_OF),
            "observations",
            (_observation(),),
        ),
        (_complete_assessment(), "confidence", 0.5),
    ),
)
def test_domain_dataclasses_are_frozen(model, attribute, replacement):
    with pytest.raises(FrozenInstanceError):
        setattr(model, attribute, replacement)


def test_public_package_exports_the_body_composition_contract():
    assert BodyCompositionObservation.__module__ == "body_composition.models"
    assert BodyMeasurement.__module__ == "body_composition.models"
    assert BodyCompositionProfile.__module__ == "body_composition.models"
    assert BodyMassTrend.__module__ == "body_composition.models"
    assert BodyCompositionDataStatus.__module__ == "body_composition.models"
    assert BodyCompositionInput.__module__ == "body_composition.models"
    assert BodyCompositionAssessment.__module__ == "body_composition.models"


def test_observation_accepts_optional_normalized_facts():
    observation = BodyCompositionObservation(VALID_FOR_DATE)

    assert observation.body_mass_kg is None
    assert observation.body_fat_percent is None
    assert observation.muscle_mass_kg is None
    assert observation.body_water_percent is None
    assert observation.visceral_fat_rating is None
    assert observation.basal_metabolic_rate_kcal is None
    assert observation.waist_circumference_cm is None
    assert observation.evidence == ()


def test_input_accepts_empty_observations_and_evidence():
    body_input = BodyCompositionInput(
        observations=(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert body_input.observations == ()
    assert body_input.evidence == ()
    assert isinstance(body_input.observations, tuple)
    assert isinstance(body_input.evidence, tuple)


def test_body_measurement_keeps_its_own_timestamp():
    observed_at = datetime(2026, 8, 1, 7, 30)
    measurement = BodyMeasurement(value=80.0, observed_at=observed_at)

    assert measurement.value == 80.0
    assert measurement.observed_at is observed_at


def test_profile_supports_metrics_from_different_timestamps():
    body_mass = BodyMeasurement(80.0, datetime(2026, 8, 3, 6))
    body_fat = BodyMeasurement(15.0, datetime(2026, 8, 1, 7))
    muscle_mass = BodyMeasurement(38.0, datetime(2026, 7, 30, 7))
    profile = BodyCompositionProfile(
        body_mass=body_mass,
        body_fat=body_fat,
        muscle_mass=muscle_mass,
    )

    assert profile.body_mass is body_mass
    assert profile.body_fat is body_fat
    assert profile.muscle_mass is muscle_mass
    assert profile.body_water is None


def test_body_mass_trend_stores_supplied_values_without_calculating():
    current = BodyMeasurement(80.0, AS_OF)
    baseline = BodyMeasurement(81.0, datetime(2026, 7, 27, 6))
    trend = BodyMassTrend(
        current=current,
        baseline=baseline,
        period_days=7,
        absolute_change_kg=-1.0,
        percentage_change=-1.234567,
    )

    assert trend.current is current
    assert trend.baseline is baseline
    assert trend.period_days == 7
    assert trend.absolute_change_kg == -1.0
    assert trend.percentage_change == -1.234567


@pytest.mark.parametrize(
    ("status", "confidence"),
    (
        (BodyCompositionDataStatus.PARTIAL, 0.25),
        (BodyCompositionDataStatus.INSUFFICIENT_DATA, 0.0),
    ),
)
def test_assessment_supports_partial_and_insufficient_contracts(
    status,
    confidence,
):
    assessment = BodyCompositionAssessment(
        profile=BodyCompositionProfile(),
        body_mass_trend=None,
        data_status=status,
        confidence=confidence,
        evidence=(),
        limitations=(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert assessment.data_status is status
    assert assessment.confidence == confidence
    assert assessment.body_mass_trend is None
    assert assessment.evidence == ()
    assert assessment.limitations == ()


def test_complete_assessment_is_a_valid_contract_construction():
    assessment = _complete_assessment()

    assert assessment.data_status is BodyCompositionDataStatus.COMPLETE
    assert assessment.confidence == 1.0
    assert assessment.body_mass_trend is not None
    assert isinstance(assessment.evidence, tuple)
    assert isinstance(assessment.limitations, tuple)


def test_construction_is_deterministic_for_identical_domain_data():
    first = BodyCompositionInput(
        observations=(_observation(),),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        evidence=("health_daily:2026-08-03",),
    )
    second = BodyCompositionInput(
        observations=(_observation(),),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        evidence=("health_daily:2026-08-03",),
    )

    assert first == second
    assert hash(first) == hash(second)
    assert _complete_assessment() == _complete_assessment()
    assert hash(_complete_assessment()) == hash(_complete_assessment())


def test_nested_tuple_contracts_cannot_be_mutated():
    observation = _observation()
    body_input = BodyCompositionInput(
        observations=(observation,),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        evidence=("health_daily:2026-08-03",),
    )

    with pytest.raises(FrozenInstanceError):
        observation.evidence += ("changed",)
    with pytest.raises(FrozenInstanceError):
        body_input.observations += (_observation(),)
    with pytest.raises(TypeError):
        body_input.observations[0] = _observation()


def test_data_status_enum_matches_the_domain_contract():
    assert tuple(BodyCompositionDataStatus) == (
        BodyCompositionDataStatus.COMPLETE,
        BodyCompositionDataStatus.PARTIAL,
        BodyCompositionDataStatus.INSUFFICIENT_DATA,
    )
    assert tuple(status.value for status in BodyCompositionDataStatus) == (
        "complete",
        "partial",
        "insufficient_data",
    )
