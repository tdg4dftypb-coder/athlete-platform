from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)
from biomarkers.intelligence import (
    Interpretation,
    ConfidenceLevel,
    CRPRule,
    BiomarkerInsightRuleRegistry,
    BiomarkerInsightAnalyzer,
)


def make_trend_with_direction(code: str, direction: TrendDirection) -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code=code,
        first_value=5.0,
        latest_value=2.0,
        absolute_change=-3.0,
        relative_change=-60.0,
        direction=direction,
        strength=TrendStrength.STRONG,
        window=TrendWindow.ALL_TIME,
        observations=3,
    )


def test_crp_rule_supports_only_crp():
    rule = CRPRule()
    assert rule.supports("crp") is True
    assert rule.supports("ferritin") is False
    assert rule.supports("glucose") is False


def test_crp_rule_increasing():
    # CRP Increasing is negative clinical outcome
    trend = make_trend_with_direction("crp", TrendDirection.INCREASING)
    rule = CRPRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "crp"
    assert insight.interpretation == Interpretation.NEGATIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "CRP is increasing."
    assert insight.reasoning == "An increasing CRP trend may indicate growing inflammation."
    assert insight.trend is trend


def test_crp_rule_decreasing():
    # CRP Decreasing is positive clinical outcome
    trend = make_trend_with_direction("crp", TrendDirection.DECREASING)
    rule = CRPRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "crp"
    assert insight.interpretation == Interpretation.POSITIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "CRP is improving."
    assert insight.reasoning == "CRP shows a decreasing trend."
    assert insight.trend is trend


def test_crp_rule_stable():
    trend = make_trend_with_direction("crp", TrendDirection.STABLE)
    rule = CRPRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "crp"
    assert insight.interpretation == Interpretation.NEUTRAL
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "CRP remains stable."
    assert insight.reasoning == "CRP trend is stable."
    assert insight.trend is trend


def test_crp_rule_insufficient_data():
    trend = make_trend_with_direction("crp", TrendDirection.INSUFFICIENT_DATA)
    rule = CRPRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "crp"
    assert insight.interpretation == Interpretation.UNKNOWN
    assert insight.confidence == ConfidenceLevel.NONE
    assert insight.summary == "Not enough data."
    assert insight.reasoning == "More measurements are required."
    assert insight.trend is trend


def test_registry_selects_crp_rule():
    trend = make_trend_with_direction("crp", TrendDirection.INCREASING)
    registry = BiomarkerInsightRuleRegistry()
    rules = registry.rules()

    # Prepend verification (second rule must be CRPRule)
    assert isinstance(rules[1], CRPRule)

    analyzer = BiomarkerInsightAnalyzer()
    insight = analyzer.analyze(trend)

    assert insight.interpretation == Interpretation.NEGATIVE
    assert insight.summary == "CRP is increasing."
