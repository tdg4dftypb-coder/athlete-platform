from datetime import datetime, timezone
from biomarkers.history import BiomarkerHistory, BiomarkerMeasurement
from biomarkers.trends import (
    BiomarkerTrendBuilder,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)
from biomarkers.models import VerificationStatus


def make_measurement(
    val: float | None, qual: str | None = None
) -> BiomarkerMeasurement:
    return BiomarkerMeasurement(
        collected_at=datetime.now(timezone.utc),
        numeric_value=val,
        qualitative_value=qual,
        laboratory_flag=None,
        verification_status=VerificationStatus.VERIFIED,
    )


def test_builder_empty_history():
    history = BiomarkerHistory(
        canonical_code="ferritin",
        display_name="Ferrytyna",
        preferred_unit="ng/mL",
        measurements=(),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.canonical_code == "ferritin"
    assert trend.first_value is None
    assert trend.latest_value is None
    assert trend.absolute_change is None
    assert trend.relative_change is None
    assert trend.observations == 0
    assert trend.direction == TrendDirection.INSUFFICIENT_DATA
    assert trend.strength == TrendStrength.NONE
    assert trend.window == TrendWindow.ALL_TIME


def test_builder_only_qualitative_history():
    history = BiomarkerHistory(
        canonical_code="hbsag",
        display_name="HBsAg",
        preferred_unit="",
        measurements=(
            make_measurement(None, "Nieobecny"),
            make_measurement(None, "Nieobecny"),
        ),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.first_value is None
    assert trend.latest_value is None
    assert trend.absolute_change is None
    assert trend.relative_change is None
    assert trend.observations == 2  # len(history.measurements)
    assert trend.direction == TrendDirection.INSUFFICIENT_DATA
    assert trend.strength == TrendStrength.NONE


def test_builder_one_numeric_value():
    history = BiomarkerHistory(
        canonical_code="ferritin",
        display_name="Ferrytyna",
        preferred_unit="ng/mL",
        measurements=(make_measurement(45.0),),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.first_value == 45.0
    assert trend.latest_value == 45.0
    assert trend.absolute_change == 0.0
    assert trend.relative_change == 0.0
    assert trend.observations == 1


def test_builder_two_numeric_values_increase():
    history = BiomarkerHistory(
        canonical_code="ferritin",
        display_name="Ferrytyna",
        preferred_unit="ng/mL",
        measurements=(make_measurement(50.0), make_measurement(75.0)),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.first_value == 50.0
    assert trend.latest_value == 75.0
    assert trend.absolute_change == 25.0
    assert trend.relative_change == 50.0  # ((75 - 50)/50) * 100
    assert trend.observations == 2


def test_builder_two_numeric_values_decrease():
    history = BiomarkerHistory(
        canonical_code="ferritin",
        display_name="Ferrytyna",
        preferred_unit="ng/mL",
        measurements=(make_measurement(80.0), make_measurement(60.0)),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.first_value == 80.0
    assert trend.latest_value == 60.0
    assert trend.absolute_change == -20.0
    assert trend.relative_change == -25.0  # ((60 - 80)/80) * 100
    assert trend.observations == 2


def test_builder_multiple_values_with_qualitative():
    # Only numeric values are analyzed, qualitative are skipped for math but included in observations count if all empty?
    # Spec: "observations = len(pomiary_liczbowe)" for >= 2 values.
    history = BiomarkerHistory(
        canonical_code="ferritin",
        display_name="Ferrytyna",
        preferred_unit="ng/mL",
        measurements=(
            make_measurement(50.0),
            make_measurement(None, "Nieobecny"),
            make_measurement(150.0),
            make_measurement(200.0),
        ),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.first_value == 50.0
    assert trend.latest_value == 200.0
    assert trend.absolute_change == 150.0
    assert trend.relative_change == 300.0  # ((200 - 50)/50) * 100
    assert trend.observations == 3  # only numeric values counted


def test_builder_first_value_zero():
    history = BiomarkerHistory(
        canonical_code="ferritin",
        display_name="Ferrytyna",
        preferred_unit="ng/mL",
        measurements=(make_measurement(0.0), make_measurement(10.0)),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.first_value == 0.0
    assert trend.latest_value == 10.0
    assert trend.absolute_change == 10.0
    assert trend.relative_change is None
    assert trend.observations == 2


def test_builder_negative_values():
    history = BiomarkerHistory(
        canonical_code="test",
        display_name="Test",
        preferred_unit="",
        measurements=(make_measurement(-10.0), make_measurement(-5.0)),
    )
    trend = BiomarkerTrendBuilder.build_trend(history)
    assert trend.first_value == -10.0
    assert trend.latest_value == -5.0
    assert trend.absolute_change == 5.0
    assert trend.relative_change == -50.0  # ((-5 - (-10)) / -10) * 100 = (5 / -10) * 100 = -50%
    assert trend.observations == 2
