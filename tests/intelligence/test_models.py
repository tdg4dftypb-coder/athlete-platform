from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from athlete.intelligence.models import (
    AthleteInsight,
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
    HealthObservationInput,
)


def test_intelligence_public_exports_match_the_canonical_contract():
    from athlete.intelligence import (
        AthleteInsight as PublicAthleteInsight,
        AthleteInsightType as PublicAthleteInsightType,
        AthleteObservation as PublicAthleteObservation,
        AthleteObservationType as PublicAthleteObservationType,
        InsightBuilder,
        InsightRule,
        ObservationProjector,
    )

    assert PublicAthleteInsight is AthleteInsight
    assert PublicAthleteInsightType is AthleteInsightType
    assert PublicAthleteObservation is AthleteObservation
    assert PublicAthleteObservationType is AthleteObservationType
    assert InsightBuilder.__module__ == "athlete.intelligence.insights"
    assert InsightRule.__module__ == "athlete.intelligence.rules"
    assert ObservationProjector.__module__ == (
        "athlete.intelligence.observation_projector"
    )


def test_observation_model_is_immutable_and_keeps_its_evidence():
    observation = AthleteObservation(
        id="execution_low:event-1",
        type=AthleteObservationType.EXECUTION_LOW,
        value=70.0,
        confidence=1.0,
        observed_at=datetime(2026, 7, 1, 8),
        evidence=("event-1",),
    )

    assert observation.evidence == ("event-1",)
    with pytest.raises(FrozenInstanceError):
        observation.value = 80.0


def test_insight_model_is_immutable_and_keeps_its_evidence():
    insight = AthleteInsight(
        id="need_more_recovery:event-1",
        type=AthleteInsightType.NEED_MORE_RECOVERY,
        confidence=1.0,
        evidence=("event-1",),
        as_of=datetime(2026, 7, 1, 8),
    )

    assert insight.evidence == ("event-1",)
    with pytest.raises(FrozenInstanceError):
        insight.confidence = 0.5


def test_observation_and_insight_type_sets_match_the_v1_contract():
    assert set(AthleteObservationType) == {
        AthleteObservationType.HRV_BELOW_BASELINE,
        AthleteObservationType.HRV_ABOVE_BASELINE,
        AthleteObservationType.SLEEP_DEBT,
        AthleteObservationType.EXECUTION_LOW,
        AthleteObservationType.TRAINING_LOAD_HIGH,
        AthleteObservationType.RECOVERY_GOOD,
    }


def test_health_observation_input_is_immutable_and_keeps_prepared_values():
    health = HealthObservationInput(
        observed_at=datetime(2026, 7, 1, 8),
        hrv_delta_percent=-5.0,
        sleep_duration_minutes=360.0,
        sleep_baseline_minutes=420.0,
        recovery_score=85.0,
        evidence=("health-day-1",),
    )

    assert health.evidence == ("health-day-1",)
    with pytest.raises(FrozenInstanceError):
        health.recovery_score = 70.0
    assert set(AthleteInsightType) == {
        AthleteInsightType.NEED_MORE_RECOVERY,
        AthleteInsightType.RESPONDS_WELL_TO_SST,
        AthleteInsightType.LIMIT_VO2_AFTER_CROSSFIT,
        AthleteInsightType.HIGH_TRAINING_COMPLIANCE,
        AthleteInsightType.FATIGUE_ACCUMULATING,
    }
