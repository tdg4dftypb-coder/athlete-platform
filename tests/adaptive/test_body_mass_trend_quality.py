from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone

import pytest

from adaptive import (
    BodyMassTrendQualityDataStatus,
    BodyMassTrendQualityEvaluator,
    BodyMassTrendQualityInput,
)
from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionProfile,
    BodyMassTrend,
    BodyMeasurement,
)


VALID_FOR_DATE = date(2026, 8, 10)
AS_OF = datetime(2026, 8, 10, 6)


def _assessment(
    *,
    period_days: int | None = 28,
    current_date: date = VALID_FOR_DATE,
    evidence: tuple[str, ...] = ("body_mass:2026-08-10",),
) -> BodyCompositionAssessment:
    current = BodyMeasurement(
        value=80.0,
        observed_at=datetime.combine(current_date, datetime.min.time()),
    )
    trend = None
    if period_days is not None:
        baseline_date = current_date - timedelta(days=period_days)
        trend = BodyMassTrend(
            current=current,
            baseline=BodyMeasurement(
                value=81.0,
                observed_at=datetime.combine(
                    baseline_date,
                    datetime.min.time(),
                ),
            ),
            period_days=period_days,
            absolute_change_kg=-1.0,
            percentage_change=-1.234567,
        )

    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(body_mass=current),
        body_mass_trend=trend,
        data_status=BodyCompositionDataStatus.PARTIAL,
        confidence=0.5,
        evidence=evidence,
        limitations=(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


def _quality_input(
    *,
    assessment: BodyCompositionAssessment | None = None,
    measurement_count: int | None = 2,
    source_consistency_known: bool = False,
    evidence: tuple[str, ...] = ("quality_input",),
) -> BodyMassTrendQualityInput:
    selected_assessment = assessment or _assessment()
    return BodyMassTrendQualityInput(
        assessment=selected_assessment,
        measurement_count=measurement_count,
        source_consistency_known=source_consistency_known,
        valid_for_date=selected_assessment.valid_for_date,
        as_of=selected_assessment.as_of,
        evidence=evidence,
    )


def test_missing_trend_and_unknown_count_are_insufficient_data():
    assessment = _assessment(period_days=None)
    assessment = BodyCompositionAssessment(
        profile=BodyCompositionProfile(),
        body_mass_trend=None,
        data_status=assessment.data_status,
        confidence=assessment.confidence,
        evidence=assessment.evidence,
        limitations=assessment.limitations,
        valid_for_date=assessment.valid_for_date,
        as_of=assessment.as_of,
    )

    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(
            assessment=assessment,
            measurement_count=None,
            evidence=(),
        )
    )

    assert quality.data_status is BodyMassTrendQualityDataStatus.INSUFFICIENT_DATA
    assert quality.confidence == 0.0
    assert quality.period_days is None
    assert quality.limitations == (
        "missing_body_mass_trend",
        "unknown_measurement_count",
        "source_consistency_unknown",
    )


@pytest.mark.parametrize("period_days", (21, 28, 35))
def test_supported_trend_windows_are_temporally_valid(period_days):
    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(assessment=_assessment(period_days=period_days))
    )

    assert quality.period_days == period_days
    assert quality.current_is_fresh is True
    assert quality.baseline_window_valid is True
    assert quality.data_status is BodyMassTrendQualityDataStatus.PARTIAL
    assert quality.confidence == 0.75
    assert quality.limitations == ("source_consistency_unknown",)


@pytest.mark.parametrize("period_days", (20, 36))
def test_period_outside_the_v1_window_is_incomplete(period_days):
    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(assessment=_assessment(period_days=period_days))
    )

    assert quality.baseline_window_valid is False
    assert quality.confidence == 0.5
    assert quality.limitations == (
        "invalid_trend_period",
        "source_consistency_unknown",
    )


def test_period_must_match_the_actual_baseline_distance():
    assessment = _assessment(period_days=28)
    trend = assessment.body_mass_trend
    assert trend is not None
    inconsistent_trend = BodyMassTrend(
        current=trend.current,
        baseline=trend.baseline,
        period_days=27,
        absolute_change_kg=trend.absolute_change_kg,
        percentage_change=trend.percentage_change,
    )
    inconsistent_assessment = BodyCompositionAssessment(
        profile=assessment.profile,
        body_mass_trend=inconsistent_trend,
        data_status=assessment.data_status,
        confidence=assessment.confidence,
        evidence=assessment.evidence,
        limitations=assessment.limitations,
        valid_for_date=assessment.valid_for_date,
        as_of=assessment.as_of,
    )

    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(assessment=inconsistent_assessment)
    )

    assert quality.baseline_window_valid is False
    assert "invalid_trend_period" in quality.limitations


@pytest.mark.parametrize(
    "measurement_count,expected_confidence,expected_limitation",
    (
        (0, 0.5, "insufficient_measurement_count"),
        (1, 0.5, "insufficient_measurement_count"),
        (2, 0.75, None),
        (8, 0.75, None),
    ),
)
def test_measurement_count_policy(
    measurement_count,
    expected_confidence,
    expected_limitation,
):
    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(measurement_count=measurement_count)
    )

    assert quality.measurement_count == measurement_count
    assert quality.confidence == expected_confidence
    assert (
        "insufficient_measurement_count" in quality.limitations
    ) is (expected_limitation is not None)


def test_unknown_measurement_count_has_a_stable_limitation():
    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(measurement_count=None)
    )

    assert quality.confidence == 0.5
    assert quality.limitations == (
        "unknown_measurement_count",
        "source_consistency_unknown",
    )


def test_stale_current_body_mass_reduces_temporal_completeness():
    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(
            assessment=_assessment(
                period_days=28,
                current_date=VALID_FOR_DATE - timedelta(days=31),
            )
        )
    )

    assert quality.current_is_fresh is False
    assert quality.baseline_window_valid is True
    assert quality.confidence == 0.5
    assert quality.limitations == (
        "stale_current_body_mass",
        "source_consistency_unknown",
    )


def test_unknown_source_consistency_prevents_complete_status():
    quality = BodyMassTrendQualityEvaluator().evaluate(_quality_input())

    assert quality.source_consistency_known is False
    assert quality.data_status is BodyMassTrendQualityDataStatus.PARTIAL
    assert quality.confidence == 0.75
    assert "source_consistency_unknown" in quality.limitations


def test_explicitly_known_source_can_complete_all_quality_sections():
    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(source_consistency_known=True)
    )

    assert quality.data_status is BodyMassTrendQualityDataStatus.COMPLETE
    assert quality.confidence == 1.0
    assert quality.limitations == ()


def test_evidence_order_is_normalized_deterministically():
    first = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(
            assessment=_assessment(evidence=("b", "a")),
            evidence=("d", "c"),
        )
    )
    second = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(
            assessment=_assessment(evidence=("a", "b")),
            evidence=("c", "d"),
        )
    )

    assert first == second
    assert first.evidence == ("a", "b", "c", "d")


def test_quality_preserves_explicit_temporal_contract():
    quality = BodyMassTrendQualityEvaluator().evaluate(_quality_input())

    assert quality.valid_for_date == VALID_FOR_DATE
    assert quality.as_of == AS_OF


def test_quality_output_is_immutable_and_assessment_is_not_mutated():
    assessment = _assessment()
    original = deepcopy(assessment)

    quality = BodyMassTrendQualityEvaluator().evaluate(
        _quality_input(assessment=assessment)
    )

    assert assessment == original
    with pytest.raises(FrozenInstanceError):
        quality.confidence = 1.0


def test_evaluator_rejects_negative_bool_and_non_integer_counts():
    evaluator = BodyMassTrendQualityEvaluator()

    with pytest.raises(ValueError, match="cannot be negative"):
        evaluator.evaluate(_quality_input(measurement_count=-1))
    for value in (True, 2.5, "2"):
        with pytest.raises(TypeError, match="measurement_count"):
            evaluator.evaluate(_quality_input(measurement_count=value))


def test_evaluator_rejects_mismatched_dates_and_mixed_timezones():
    quality_input = _quality_input()
    mismatched_date = BodyMassTrendQualityInput(
        assessment=quality_input.assessment,
        measurement_count=2,
        source_consistency_known=False,
        valid_for_date=date(2026, 8, 9),
        as_of=AS_OF,
    )
    aware_as_of = AS_OF.replace(tzinfo=timezone.utc)
    mixed_timezones = BodyMassTrendQualityInput(
        assessment=quality_input.assessment,
        measurement_count=2,
        source_consistency_known=False,
        valid_for_date=VALID_FOR_DATE,
        as_of=aware_as_of,
    )

    with pytest.raises(ValueError, match="valid_for_date must match"):
        BodyMassTrendQualityEvaluator().evaluate(mismatched_date)
    with pytest.raises(ValueError, match="compatible timezones"):
        BodyMassTrendQualityEvaluator().evaluate(mixed_timezones)
