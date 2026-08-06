import pytest
from biomarkers.trends import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
    TrendClassifier,
)


def make_trend(
    relative_change: float | None, observations: int
) -> BiomarkerTrend:
    return BiomarkerTrend(
        canonical_code="ferritin",
        first_value=100.0,
        latest_value=110.0,
        absolute_change=10.0,
        relative_change=relative_change,
        direction=TrendDirection.INSUFFICIENT_DATA,
        strength=TrendStrength.NONE,
        window=TrendWindow.ALL_TIME,
        observations=observations,
    )


def test_classifier_insufficient_data_due_to_observations():
    # observations < 2 -> INSUFFICIENT_DATA / NONE
    t = make_trend(relative_change=10.0, observations=1)
    res = TrendClassifier.classify(t)
    assert res.direction == TrendDirection.INSUFFICIENT_DATA
    assert res.strength == TrendStrength.NONE


def test_classifier_insufficient_data_due_to_relative_change():
    # relative_change is None -> INSUFFICIENT_DATA / NONE
    t = make_trend(relative_change=None, observations=3)
    res = TrendClassifier.classify(t)
    assert res.direction == TrendDirection.INSUFFICIENT_DATA
    assert res.strength == TrendStrength.NONE


def test_classifier_stable_limits():
    # Exactly 5% change -> STABLE / NONE
    t_pos = make_trend(relative_change=5.0, observations=2)
    res_pos = TrendClassifier.classify(t_pos)
    assert res_pos.direction == TrendDirection.STABLE
    assert res_pos.strength == TrendStrength.NONE

    # Exactly -5% change -> STABLE / NONE
    t_neg = make_trend(relative_change=-5.0, observations=2)
    res_neg = TrendClassifier.classify(t_neg)
    assert res_neg.direction == TrendDirection.STABLE
    assert res_neg.strength == TrendStrength.NONE

    # Within stable bounds (e.g. 4.9%) -> STABLE / NONE
    t_mid = make_trend(relative_change=4.9, observations=2)
    res_mid = TrendClassifier.classify(t_mid)
    assert res_mid.direction == TrendDirection.STABLE
    assert res_mid.strength == TrendStrength.NONE


def test_classifier_increasing_decreasing():
    # +6% -> INCREASING / WEAK
    t_inc = make_trend(relative_change=6.0, observations=2)
    res_inc = TrendClassifier.classify(t_inc)
    assert res_inc.direction == TrendDirection.INCREASING
    assert res_inc.strength == TrendStrength.WEAK

    # -6% -> DECREASING / WEAK
    t_dec = make_trend(relative_change=-6.0, observations=2)
    res_dec = TrendClassifier.classify(t_dec)
    assert res_dec.direction == TrendDirection.DECREASING
    assert res_dec.strength == TrendStrength.WEAK


def test_classifier_strength_weak_edge():
    # Exactly 15% -> WEAK (5-15% range is inclusive of upper bound)
    t = make_trend(relative_change=15.0, observations=3)
    res = TrendClassifier.classify(t)
    assert res.direction == TrendDirection.INCREASING
    assert res.strength == TrendStrength.WEAK

    # 14% -> WEAK
    t2 = make_trend(relative_change=14.0, observations=3)
    res2 = TrendClassifier.classify(t2)
    assert res2.direction == TrendDirection.INCREASING
    assert res2.strength == TrendStrength.WEAK


def test_classifier_strength_moderate_edge():
    # Exactly 30% -> MODERATE (15-30% range inclusive)
    t = make_trend(relative_change=30.0, observations=3)
    res = TrendClassifier.classify(t)
    assert res.direction == TrendDirection.INCREASING
    assert res.strength == TrendStrength.MODERATE

    # 31% -> STRONG
    t2 = make_trend(relative_change=31.0, observations=3)
    res2 = TrendClassifier.classify(t2)
    assert res2.direction == TrendDirection.INCREASING
    assert res2.strength == TrendStrength.STRONG


def test_classifier_immutability():
    # Ensure original trend is not mutated
    t = make_trend(relative_change=45.0, observations=5)
    res = TrendClassifier.classify(t)
    
    assert t.direction == TrendDirection.INSUFFICIENT_DATA
    assert t.strength == TrendStrength.NONE
    
    assert res.direction == TrendDirection.INCREASING
    assert res.strength == TrendStrength.STRONG
    assert t is not res
