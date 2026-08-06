from dataclasses import FrozenInstanceError
import pytest
from biomarkers.trends import (
    TrendDirection,
    TrendStrength,
    TrendWindow,
    BiomarkerTrend,
)


def test_trend_direction_enum():
    assert TrendDirection.INCREASING.name == "INCREASING"
    assert TrendDirection.DECREASING.name == "DECREASING"
    assert TrendDirection.STABLE.name == "STABLE"
    assert TrendDirection.INSUFFICIENT_DATA.name == "INSUFFICIENT_DATA"


def test_trend_strength_enum():
    assert TrendStrength.NONE.name == "NONE"
    assert TrendStrength.WEAK.name == "WEAK"
    assert TrendStrength.MODERATE.name == "MODERATE"
    assert TrendStrength.STRONG.name == "STRONG"


def test_trend_window_enum():
    assert TrendWindow.ALL_TIME.name == "ALL_TIME"


def test_biomarker_trend_creation():
    trend = BiomarkerTrend(
        canonical_code="ferritin",
        first_value=30.0,
        latest_value=120.0,
        absolute_change=90.0,
        relative_change=3.0,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.STRONG,
        window=TrendWindow.ALL_TIME,
        observations=4,
    )
    assert trend.canonical_code == "ferritin"
    assert trend.first_value == 30.0
    assert trend.latest_value == 120.0
    assert trend.absolute_change == 90.0
    assert trend.relative_change == 3.0
    assert trend.direction == TrendDirection.INCREASING
    assert trend.strength == TrendStrength.STRONG
    assert trend.window == TrendWindow.ALL_TIME
    assert trend.observations == 4


def test_biomarker_trend_immutability():
    trend = BiomarkerTrend(
        canonical_code="ferritin",
        first_value=30.0,
        latest_value=120.0,
        absolute_change=90.0,
        relative_change=3.0,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.STRONG,
        window=TrendWindow.ALL_TIME,
        observations=4,
    )
    with pytest.raises(FrozenInstanceError):
        trend.canonical_code = "glucose"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        trend.observations = 5  # type: ignore


def test_biomarker_trend_equality():
    trend1 = BiomarkerTrend(
        canonical_code="ferritin",
        first_value=30.0,
        latest_value=120.0,
        absolute_change=90.0,
        relative_change=3.0,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.STRONG,
        window=TrendWindow.ALL_TIME,
        observations=4,
    )
    trend2 = BiomarkerTrend(
        canonical_code="ferritin",
        first_value=30.0,
        latest_value=120.0,
        absolute_change=90.0,
        relative_change=3.0,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.STRONG,
        window=TrendWindow.ALL_TIME,
        observations=4,
    )
    trend3 = BiomarkerTrend(
        canonical_code="ferritin",
        first_value=30.0,
        latest_value=110.0,  # different
        absolute_change=80.0,
        relative_change=2.67,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.MODERATE,
        window=TrendWindow.ALL_TIME,
        observations=4,
    )
    assert trend1 == trend2
    assert trend1 != trend3


def test_biomarker_trend_repr():
    trend = BiomarkerTrend(
        canonical_code="ferritin",
        first_value=30.0,
        latest_value=120.0,
        absolute_change=90.0,
        relative_change=3.0,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.STRONG,
        window=TrendWindow.ALL_TIME,
        observations=4,
    )
    rep = repr(trend)
    assert "BiomarkerTrend" in rep
    assert "canonical_code='ferritin'" in rep
    assert "direction=<TrendDirection.INCREASING:" in rep
