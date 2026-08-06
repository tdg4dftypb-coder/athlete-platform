from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)
from biomarkers.intelligence import (
    Interpretation,
    ConfidenceLevel,
    VitaminDRule,
    BiomarkerInsightRuleRegistry,
    BiomarkerInsightAnalyzer,
)


def make_trend_with_direction(code: str, direction: TrendDirection) -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code=code,
        first_value=30.0,
        latest_value=30.0,
        absolute_change=0.0,
        relative_change=0.0,
        direction=direction,
        strength=TrendStrength.NONE,
        window=TrendWindow.ALL_TIME,
        observations=3,
    )


def test_vitamin_d_rule_supports_only_vitamin_d_25_oh():
    rule = VitaminDRule()
    assert rule.supports("vitamin_d_25_oh") is True
    assert rule.supports("vitamin_d") is False
    assert rule.supports("ferritin") is False
    assert rule.supports("crp") is False


def test_vitamin_d_rule_increasing():
    trend = make_trend_with_direction("vitamin_d_25_oh", TrendDirection.INCREASING)
    rule = VitaminDRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "vitamin_d_25_oh"
    assert insight.interpretation == Interpretation.POSITIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "Vitamin D is improving."
    assert insight.reasoning == "Vitamin D shows an increasing trend."
    assert insight.trend is trend


def test_vitamin_d_rule_stable():
    # Vitamin D Stable is clinically positive outcome
    trend = make_trend_with_direction("vitamin_d_25_oh", TrendDirection.STABLE)
    rule = VitaminDRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "vitamin_d_25_oh"
    assert insight.interpretation == Interpretation.POSITIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "Vitamin D remains stable."
    assert insight.reasoning == "Vitamin D remains at a stable level."
    assert insight.trend is trend


def test_vitamin_d_rule_decreasing():
    # Vitamin D Decreasing is clinically negative outcome
    trend = make_trend_with_direction("vitamin_d_25_oh", TrendDirection.DECREASING)
    rule = VitaminDRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "vitamin_d_25_oh"
    assert insight.interpretation == Interpretation.NEGATIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "Vitamin D is decreasing."
    assert insight.reasoning == "Vitamin D shows a decreasing trend."
    assert insight.trend is trend


def test_vitamin_d_rule_insufficient_data():
    trend = make_trend_with_direction("vitamin_d_25_oh", TrendDirection.INSUFFICIENT_DATA)
    rule = VitaminDRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "vitamin_d_25_oh"
    assert insight.interpretation == Interpretation.UNKNOWN
    assert insight.confidence == ConfidenceLevel.NONE
    assert insight.summary == "Not enough data."
    assert insight.reasoning == "More measurements are required."
    assert insight.trend is trend


def test_registry_selects_vitamin_d_rule():
    trend = make_trend_with_direction("vitamin_d_25_oh", TrendDirection.STABLE)
    registry = BiomarkerInsightRuleRegistry()
    rules = registry.rules()

    # Prepend verification (third rule must be VitaminDRule)
    assert isinstance(rules[2], VitaminDRule)

    analyzer = BiomarkerInsightAnalyzer()
    insight = analyzer.analyze(trend)

    assert insight.interpretation == Interpretation.POSITIVE
    assert insight.summary == "Vitamin D remains stable."
