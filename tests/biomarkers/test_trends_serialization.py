from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
    BiomarkerTrendSerializer,
)


def test_serialize_complete_trend():
    trend = BiomarkerTrend(
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

    data = BiomarkerTrendSerializer.serialize(trend)

    # Validate keys
    expected_keys = {
        "canonical_code",
        "first_value",
        "latest_value",
        "absolute_change",
        "relative_change",
        "direction",
        "strength",
        "window",
        "observations",
    }
    assert set(data.keys()) == expected_keys

    # Validate values mapping
    assert data["canonical_code"] == "ferritin"
    assert data["first_value"] == 30.0
    assert data["latest_value"] == 120.0
    assert data["absolute_change"] == 90.0
    assert data["relative_change"] == 300.0
    assert data["direction"] == "increasing"  # lowercase
    assert data["strength"] == "strong"        # lowercase
    assert data["window"] == "all_time"        # lowercase
    assert data["observations"] == 4


def test_serialize_none_values():
    trend = BiomarkerTrend(
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

    data = BiomarkerTrendSerializer.serialize(trend)

    assert data["canonical_code"] == "ferritin"
    assert data["first_value"] is None
    assert data["latest_value"] is None
    assert data["absolute_change"] is None
    assert data["relative_change"] is None
    assert data["direction"] == "insufficient_data"
    assert data["strength"] == "none"
    assert data["window"] == "all_time"
    assert data["observations"] == 0


def test_serialize_all_enum_variants():
    # Helper to check conversion
    def get_serialized_enums(direction, strength, window):
        trend = BiomarkerTrend(
            canonical_code="test",
            first_value=1.0,
            latest_value=1.0,
            absolute_change=0.0,
            relative_change=0.0,
            direction=direction,
            strength=strength,
            window=window,
            observations=2,
        )
        serialized = BiomarkerTrendSerializer.serialize(trend)
        return serialized["direction"], serialized["strength"], serialized["window"]

    # Direction variants
    assert get_serialized_enums(TrendDirection.INCREASING, TrendStrength.NONE, TrendWindow.ALL_TIME) == ("increasing", "none", "all_time")
    assert get_serialized_enums(TrendDirection.DECREASING, TrendStrength.NONE, TrendWindow.ALL_TIME) == ("decreasing", "none", "all_time")
    assert get_serialized_enums(TrendDirection.STABLE, TrendStrength.NONE, TrendWindow.ALL_TIME) == ("stable", "none", "all_time")
    assert get_serialized_enums(TrendDirection.INSUFFICIENT_DATA, TrendStrength.NONE, TrendWindow.ALL_TIME) == ("insufficient_data", "none", "all_time")

    # Strength variants
    assert get_serialized_enums(TrendDirection.STABLE, TrendStrength.WEAK, TrendWindow.ALL_TIME)[1] == "weak"
    assert get_serialized_enums(TrendDirection.STABLE, TrendStrength.MODERATE, TrendWindow.ALL_TIME)[1] == "moderate"
    assert get_serialized_enums(TrendDirection.STABLE, TrendStrength.STRONG, TrendWindow.ALL_TIME)[1] == "strong"
