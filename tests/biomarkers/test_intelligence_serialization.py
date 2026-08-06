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
    BiomarkerInsightSerializer,
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


def test_serialize_complete_insight():
    trend = make_dummy_trend()
    insight = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.POSITIVE,
        confidence=ConfidenceLevel.HIGH,
        summary="Summary test",
        reasoning="Reasoning test",
        trend=trend,
    )

    data = BiomarkerInsightSerializer.serialize(insight)

    # Validate top-level keys
    expected_keys = {
        "canonical_code",
        "interpretation",
        "confidence",
        "summary",
        "reasoning",
        "trend",
    }
    assert set(data.keys()) == expected_keys

    # Validate mapping
    assert data["canonical_code"] == "ferritin"
    assert data["interpretation"] == "positive"  # lowercase
    assert data["confidence"] == "high"          # lowercase
    assert data["summary"] == "Summary test"
    assert data["reasoning"] == "Reasoning test"

    # Validate nested trend serialization (composition)
    assert isinstance(data["trend"], dict)
    assert data["trend"]["canonical_code"] == "ferritin"
    assert data["trend"]["first_value"] == 30.0
    assert data["trend"]["latest_value"] == 120.0
    assert data["trend"]["absolute_change"] == 90.0
    assert data["trend"]["relative_change"] == 300.0
    assert data["trend"]["direction"] == "increasing"
    assert data["trend"]["strength"] == "strong"
    assert data["trend"]["window"] == "all_time"
    assert data["trend"]["observations"] == 4


def test_serialize_insight_with_none_values():
    trend = make_dummy_trend()
    insight = BiomarkerInsight(
        canonical_code="ferritin",
        interpretation=Interpretation.UNKNOWN,
        confidence=ConfidenceLevel.NONE,
        summary=None,
        reasoning=None,
        trend=trend,
    )

    data = BiomarkerInsightSerializer.serialize(insight)

    assert data["summary"] is None
    assert data["reasoning"] is None
    assert data["interpretation"] == "unknown"
    assert data["confidence"] == "none"


def test_serialize_all_interpretation_and_confidence_variants():
    # Helper to check conversion
    def get_serialized_enums(interpretation, confidence):
        trend = make_dummy_trend()
        insight = BiomarkerInsight(
            canonical_code="test",
            interpretation=interpretation,
            confidence=confidence,
            summary="S",
            reasoning="R",
            trend=trend,
        )
        serialized = BiomarkerInsightSerializer.serialize(insight)
        return serialized["interpretation"], serialized["confidence"]

    # Interpretation variants
    assert get_serialized_enums(Interpretation.UNKNOWN, ConfidenceLevel.NONE) == ("unknown", "none")
    assert get_serialized_enums(Interpretation.POSITIVE, ConfidenceLevel.NONE) == ("positive", "none")
    assert get_serialized_enums(Interpretation.NEGATIVE, ConfidenceLevel.NONE) == ("negative", "none")
    assert get_serialized_enums(Interpretation.NEUTRAL, ConfidenceLevel.NONE) == ("neutral", "none")

    # Confidence variants
    assert get_serialized_enums(Interpretation.NEUTRAL, ConfidenceLevel.LOW)[1] == "low"
    assert get_serialized_enums(Interpretation.NEUTRAL, ConfidenceLevel.MEDIUM)[1] == "medium"
    assert get_serialized_enums(Interpretation.NEUTRAL, ConfidenceLevel.HIGH)[1] == "high"
