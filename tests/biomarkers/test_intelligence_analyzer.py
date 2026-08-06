import pytest
from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)
from biomarkers.intelligence import (
    BiomarkerInsight,
    Interpretation,
    ConfidenceLevel,
    BiomarkerInsightRule,
    BiomarkerInsightAnalyzer,
)


class StubRule(BiomarkerInsightRule):
    def __init__(self, supported_code: str, insight: BiomarkerInsight) -> None:
        self.supported_code = supported_code
        self.insight = insight
        self.called_with = None

    def supports(self, canonical_code: str) -> bool:
        return canonical_code == self.supported_code

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        self.called_with = trend
        return self.insight


def make_dummy_trend(code: str) -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code=code,
        first_value=100.0,
        latest_value=120.0,
        absolute_change=20.0,
        relative_change=20.0,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.MODERATE,
        window=TrendWindow.ALL_TIME,
        observations=2,
    )


def make_dummy_insight(code: str, summary: str) -> BiomarkerInsight:
    return BiomarkerInsight(
        canonical_code=code,
        interpretation=Interpretation.NEUTRAL,
        confidence=ConfidenceLevel.LOW,
        summary=summary,
        reasoning="Reason",
        trend=make_dummy_trend(code),
    )


def test_analyzer_evaluates_first_matching_rule():
    trend = make_dummy_trend("ferritin")
    insight1 = make_dummy_insight("ferritin", "First match wins")
    insight2 = make_dummy_insight("ferritin", "Second match should be ignored")

    rule1 = StubRule("ferritin", insight1)
    rule2 = StubRule("ferritin", insight2)

    analyzer = BiomarkerInsightAnalyzer(rules=[rule1, rule2])
    result = analyzer.analyze(trend)

    assert result is insight1
    assert rule1.called_with is trend
    assert rule2.called_with is None  # Short-circuit


def test_analyzer_skips_non_matching_rules():
    trend = make_dummy_trend("glucose")
    insight = make_dummy_insight("glucose", "Insight for glucose")

    rule1 = StubRule("ferritin", make_dummy_insight("ferritin", "F"))
    rule2 = StubRule("glucose", insight)

    analyzer = BiomarkerInsightAnalyzer(rules=[rule1, rule2])
    result = analyzer.analyze(trend)

    assert result is insight
    assert rule1.called_with is None
    assert rule2.called_with is trend


def test_analyzer_raises_lookup_error_if_no_rule_matches():
    trend = make_dummy_trend("cortisol")
    rule = StubRule("ferritin", make_dummy_insight("ferritin", "F"))

    analyzer = BiomarkerInsightAnalyzer(rules=[rule])
    with pytest.raises(LookupError) as excinfo:
        analyzer.analyze(trend)

    assert "No registered intelligence rule supports biomarker 'cortisol'" in str(
        excinfo.value
    )


def test_analyzer_dependency_injection():
    # Verify construct stores custom rules
    custom_rules = [StubRule("ferritin", make_dummy_insight("ferritin", "F"))]
    analyzer = BiomarkerInsightAnalyzer(rules=custom_rules)
    assert analyzer._rules is custom_rules
