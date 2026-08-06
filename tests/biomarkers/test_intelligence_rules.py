import pytest
from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)
from biomarkers.intelligence import (
    Interpretation,
    ConfidenceLevel,
    GenericIncreasingRule,
    GenericDecreasingRule,
    GenericStableRule,
    GenericUnknownRule,
)


def make_trend_with_direction(direction: TrendDirection) -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code="glucose",
        first_value=100.0,
        latest_value=110.0,
        absolute_change=10.0,
        relative_change=10.0,
        direction=direction,
        strength=TrendStrength.MODERATE,
        window=TrendWindow.ALL_TIME,
        observations=3,
    )


def test_rules_support_any_biomarker():
    rules = [
        GenericIncreasingRule(),
        GenericDecreasingRule(),
        GenericStableRule(),
        GenericUnknownRule(),
    ]
    for r in rules:
        assert r.supports("ferritin") is True
        assert r.supports("glucose") is True
        assert r.supports("any_random_code") is True


def test_generic_increasing_rule():
    trend = make_trend_with_direction(TrendDirection.INCREASING)
    rule = GenericIncreasingRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "glucose"
    assert insight.interpretation == Interpretation.UNKNOWN
    assert insight.confidence == ConfidenceLevel.NONE
    assert insight.summary == "Biomarker shows an increasing trend."
    assert insight.reasoning == "Generic trend interpretation."
    assert insight.trend is trend


def test_generic_decreasing_rule():
    trend = make_trend_with_direction(TrendDirection.DECREASING)
    rule = GenericDecreasingRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "glucose"
    assert insight.interpretation == Interpretation.UNKNOWN
    assert insight.confidence == ConfidenceLevel.NONE
    assert insight.summary == "Biomarker shows a decreasing trend."
    assert insight.reasoning == "Generic trend interpretation."
    assert insight.trend is trend


def test_generic_stable_rule():
    trend = make_trend_with_direction(TrendDirection.STABLE)
    rule = GenericStableRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "glucose"
    assert insight.interpretation == Interpretation.UNKNOWN
    assert insight.confidence == ConfidenceLevel.NONE
    assert insight.summary == "Biomarker shows a stable trend."
    assert insight.reasoning == "Generic trend interpretation."
    assert insight.trend is trend


def test_generic_unknown_rule():
    trend = make_trend_with_direction(TrendDirection.INSUFFICIENT_DATA)
    rule = GenericUnknownRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "glucose"
    assert insight.interpretation == Interpretation.UNKNOWN
    assert insight.confidence == ConfidenceLevel.NONE
    assert insight.summary == "Biomarker trend interpretation is unavailable."
    assert insight.reasoning == "Generic trend interpretation."
    assert insight.trend is trend
