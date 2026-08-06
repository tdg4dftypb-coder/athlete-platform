from datetime import datetime, timezone
from biomarkers.history import BiomarkerHistory, BiomarkerMeasurement
from biomarkers.trends import (
    BiomarkerTrendAnalyzer,
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
    BiomarkerTrendBuilder,
    TrendClassifier,
)
from biomarkers.models import VerificationStatus


class StubBuilder(BiomarkerTrendBuilder):
    def __init__(self, stub_trend: BiomarkerTrend) -> None:
        self.stub_trend = stub_trend
        self.called_with = None

    def build_trend(self, history: BiomarkerHistory) -> BiomarkerTrend:
        self.called_with = history
        return self.stub_trend


class StubClassifier(TrendClassifier):
    def __init__(self, stub_trend: BiomarkerTrend) -> None:
        self.stub_trend = stub_trend
        self.called_with = None

    def classify(self, trend: BiomarkerTrend) -> BiomarkerTrend:
        self.called_with = trend
        return self.stub_trend


def make_empty_trend() -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code="ferritin",
        first_value=None,
        latest_value=None,
        absolute_change=None,
        relative_change=None,
        direction=TrendDirection.INSUFFICIENT_DATA,
        strength=TrendStrength.NONE,
        window=TrendWindow.ALL_TIME,
        observations=0,
    )


def test_analyzer_default_pipeline():
    history = BiomarkerHistory(
        canonical_code="ferritin",
        display_name="Ferrytyna",
        preferred_unit="ng/mL",
        measurements=(
            BiomarkerMeasurement(
                collected_at=datetime.now(timezone.utc),
                numeric_value=100.0,
                qualitative_value=None,
                laboratory_flag=None,
                verification_status=VerificationStatus.VERIFIED,
            ),
            BiomarkerMeasurement(
                collected_at=datetime.now(timezone.utc),
                numeric_value=150.0,
                qualitative_value=None,
                laboratory_flag=None,
                verification_status=VerificationStatus.VERIFIED,
            ),
        ),
    )

    analyzer = BiomarkerTrendAnalyzer()
    trend = analyzer.analyze(history)

    assert trend.canonical_code == "ferritin"
    assert trend.first_value == 100.0
    assert trend.latest_value == 150.0
    assert trend.absolute_change == 50.0
    assert trend.relative_change == 50.0
    assert trend.direction == TrendDirection.INCREASING
    assert trend.strength == TrendStrength.STRONG
    assert trend.observations == 2


def test_analyzer_dependency_injection():
    history = BiomarkerHistory(
        canonical_code="glucose",
        display_name="Glukoza",
        preferred_unit="mg/dL",
        measurements=(),
    )

    intermediate_trend = make_empty_trend()
    final_trend = BiomarkerTrend(
        canonical_code="glucose",
        first_value=90.0,
        latest_value=95.0,
        absolute_change=5.0,
        relative_change=5.56,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.WEAK,
        window=TrendWindow.ALL_TIME,
        observations=2,
    )

    stub_builder = StubBuilder(intermediate_trend)
    stub_classifier = StubClassifier(final_trend)

    analyzer = BiomarkerTrendAnalyzer(builder=stub_builder, classifier=stub_classifier)
    result = analyzer.analyze(history)

    assert stub_builder.called_with is history
    assert stub_classifier.called_with is intermediate_trend
    assert result is final_trend
