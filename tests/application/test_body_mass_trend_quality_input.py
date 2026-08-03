from copy import deepcopy
from datetime import date, datetime

import pytest

from application.body_mass_trend_quality_input import (
    BodyMassTrendQualityInputBuilder,
)
from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionInput,
    BodyCompositionObservation,
    BodyCompositionProfile,
)


VALID_FOR_DATE = date(2026, 8, 10)
AS_OF = datetime(2026, 8, 10, 6)


def _assessment() -> BodyCompositionAssessment:
    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(),
        body_mass_trend=None,
        data_status=BodyCompositionDataStatus.PARTIAL,
        confidence=0.25,
        evidence=("assessment",),
        limitations=("insufficient_body_mass_history",),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


def _body_input() -> BodyCompositionInput:
    return BodyCompositionInput(
        observations=(
            BodyCompositionObservation(
                observed_for_date=date(2026, 7, 13),
                body_mass_kg=81.0,
            ),
            BodyCompositionObservation(
                observed_for_date=date(2026, 8, 10),
                body_mass_kg=80.0,
            ),
            BodyCompositionObservation(
                observed_for_date=date(2026, 8, 10),
                body_mass_kg=80.0,
            ),
            BodyCompositionObservation(
                observed_for_date=date(2026, 8, 9),
                body_fat_percent=15.0,
            ),
        ),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        evidence=("input",),
    )


def test_builder_counts_distinct_dated_body_mass_measurements():
    assessment = _assessment()
    body_input = _body_input()

    result = BodyMassTrendQualityInputBuilder().build(
        assessment,
        body_input,
    )

    assert result.assessment is assessment
    assert result.measurement_count == 2
    assert result.source_consistency_known is False
    assert result.valid_for_date == VALID_FOR_DATE
    assert result.as_of == AS_OF
    assert result.evidence == ("assessment", "input")


def test_builder_is_deterministic_and_does_not_mutate_inputs():
    assessment = _assessment()
    body_input = _body_input()
    original_assessment = deepcopy(assessment)
    original_input = deepcopy(body_input)
    builder = BodyMassTrendQualityInputBuilder()

    first = builder.build(assessment, body_input)
    second = builder.build(assessment, body_input)

    assert first == second
    assert assessment == original_assessment
    assert body_input == original_input


def test_builder_rejects_mismatched_assessment_temporal_contract():
    body_input = _body_input()
    mismatched_date = BodyCompositionInput(
        observations=body_input.observations,
        valid_for_date=date(2026, 8, 9),
        as_of=AS_OF,
    )
    mismatched_time = BodyCompositionInput(
        observations=body_input.observations,
        valid_for_date=VALID_FOR_DATE,
        as_of=datetime(2026, 8, 10, 7),
    )
    builder = BodyMassTrendQualityInputBuilder()

    with pytest.raises(ValueError, match="valid_for_date must match"):
        builder.build(_assessment(), mismatched_date)
    with pytest.raises(ValueError, match="as_of must match"):
        builder.build(_assessment(), mismatched_time)
