from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)
from biomarkers.intelligence import (
    Interpretation,
    ConfidenceLevel,
    FerritinRule,
    BiomarkerInsightRuleRegistry,
    BiomarkerInsightAnalyzer,
)


def make_trend_with_direction(code: str, direction: TrendDirection) -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code=code,
        first_value=100.0,
        latest_value=110.0,
        absolute_change=10.0,
        relative_change=10.0,
        direction=direction,
        strength=TrendStrength.MODERATE,
        window=TrendWindow.ALL_TIME,
        observations=3,
    )


def test_ferritin_rule_supports_only_ferritin():
    rule = FerritinRule()
    assert rule.supports("ferritin") is True
    assert rule.supports("glucose") is False
    assert rule.supports("any_other") is False


def test_ferritin_rule_increasing():
    trend = make_trend_with_direction("ferritin", TrendDirection.INCREASING)
    rule = FerritinRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "ferritin"
    assert insight.interpretation == Interpretation.POSITIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "Ferritin is improving."
    assert insight.reasoning == "Ferritin shows an increasing trend."
    assert insight.trend is trend


def test_ferritin_rule_decreasing():
    trend = make_trend_with_direction("ferritin", TrendDirection.DECREASING)
    rule = FerritinRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "ferritin"
    assert insight.interpretation == Interpretation.NEGATIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "Ferritin is decreasing."
    assert insight.reasoning == "Ferritin shows a decreasing trend."
    assert insight.trend is trend


def test_ferritin_rule_stable():
    trend = make_trend_with_direction("ferritin", TrendDirection.STABLE)
    rule = FerritinRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "ferritin"
    assert insight.interpretation == Interpretation.NEUTRAL
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "Ferritin remains stable."
    assert insight.reasoning == "Generic trend interpretation."
    assert insight.trend is trend


def test_ferritin_rule_insufficient_data():
    trend = make_trend_with_direction("ferritin", TrendDirection.INSUFFICIENT_DATA)
    rule = FerritinRule()
    insight = rule.evaluate(trend)

    assert insight.canonical_code == "ferritin"
    assert insight.interpretation == Interpretation.UNKNOWN
    assert insight.confidence == ConfidenceLevel.NONE
    assert insight.summary == "Biomarker trend interpretation is unavailable."
    assert insight.reasoning == "Generic trend interpretation."
    assert insight.trend is trend


def test_registry_selects_ferritin_rule_instead_of_generic():
    # Integrate Registry and Analyzer, pass ferritin trend
    trend = make_trend_with_direction("ferritin", TrendDirection.INCREASING)
    
    # Register has FerritinRule in default rules
    registry = BiomarkerInsightRuleRegistry()
    rules = registry.rules()
    
    # Prepend verification
    assert isinstance(rules[0], FerritinRule)
    
    analyzer = BiomarkerInsightAnalyzer()
    insight = analyzer.analyze(trend)
    
    # It must evaluate via FerritinRule (Improving summary) rather than GenericIncreasingRule (increasing trend)
    assert insight.interpretation == Interpretation.POSITIVE
    assert insight.summary == "Ferritin is improving."
