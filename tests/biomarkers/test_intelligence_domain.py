from dataclasses import FrozenInstanceError
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
    BiomarkerInsight,
)


def make_dummy_trend() -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code="ferritin",
        first_value=30.0,
        latest_value=120.0,
        absolute_change=90.0,
        relative_change=300.0,
        direction=TrendDirection.INCREASING,
        strength=TrendStrength.STRONG,
        window=TrendWindow.ALL_TIME,
        observations=4,
    )


def test_interpretation_enum():
    assert Interpretation.UNKNOWN.name == "UNKNOWN"
    assert Interpretation.POSITIVE.name == "POSITIVE"
    assert Interpretation.NEGATIVE.name == "NEGATIVE"
    assert Interpretation.NEUTRAL.name == "NEUTRAL"


def test_confidence_level_enum():
    assert ConfidenceLevel.NONE.name == "NONE"
    assert ConfidenceLevel.LOW.name == "LOW"
    assert ConfidenceLevel.MEDIUM.name == "MEDIUM"
    assert ConfidenceLevel.HIGH.name == "HIGH"


def test_biomarker_insight_creation():
    trend = make_dummy_trend()
    insight = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.POSITIVE,
        confidence=ConfidenceLevel.HIGH,
        summary="Ferrytyna rośnie prawidłowo.",
        reasoning="Zaobserwowano systematyczny wzrost o 90.0 ng/mL.",
        trend=trend,
    )

    assert insight.canonical_code == "ferritin"
    assert insight.interpretation == Interpretation.POSITIVE
    assert insight.confidence == ConfidenceLevel.HIGH
    assert insight.summary == "Ferrytyna rośnie prawidłowo."
    assert insight.reasoning == "Zaobserwowano systematyczny wzrost o 90.0 ng/mL."
    assert insight.trend is trend


def test_biomarker_insight_immutability():
    trend = make_dummy_trend()
    insight = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.POSITIVE,
        confidence=ConfidenceLevel.HIGH,
        summary="Summary",
        reasoning="Reasoning",
        trend=trend,
    )

    with pytest.raises(FrozenInstanceError):
        insight.canonical_code = "glucose"  # type: ignore

    with pytest.raises(FrozenInstanceError):
        insight.interpretation = Interpretation.NEGATIVE  # type: ignore


def test_biomarker_insight_equality():
    trend = make_dummy_trend()
    insight1 = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.POSITIVE,
        confidence=ConfidenceLevel.HIGH,
        summary="Summary",
        reasoning="Reasoning",
        trend=trend,
    )
    insight2 = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.POSITIVE,
        confidence=ConfidenceLevel.HIGH,
        summary="Summary",
        reasoning="Reasoning",
        trend=trend,
    )
    insight3 = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.NEUTRAL,
        confidence=ConfidenceLevel.HIGH,
        summary="Summary",
        reasoning="Reasoning",
        trend=trend,
    )

    assert insight1 == insight2
    assert insight1 != insight3


def test_biomarker_insight_repr():
    trend = make_dummy_trend()
    insight = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.POSITIVE,
        confidence=ConfidenceLevel.HIGH,
        summary="Summary",
        reasoning="Reasoning",
        trend=trend,
    )

    rep = repr(insight)
    assert "BiomarkerInsight" in rep
    assert "canonical_code='ferritin'" in rep
    assert "interpretation=<Interpretation.POSITIVE:" in rep
    assert "confidence=<ConfidenceLevel.HIGH:" in rep
