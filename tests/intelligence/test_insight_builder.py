from datetime import datetime, timedelta

from athlete.intelligence.insights import InsightBuilder
from athlete.intelligence.models import (
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
)


def _observation(
    observation_type: AthleteObservationType,
    event_id: str,
    *,
    confidence: float = 1.0,
    observed_at: datetime = datetime(2026, 7, 1, 8),
) -> AthleteObservation:
    return AthleteObservation(
        id=f"{observation_type.value}:{event_id}",
        type=observation_type,
        value=1.0,
        confidence=confidence,
        observed_at=observed_at,
        evidence=(event_id,),
    )


def test_builder_maps_same_moment_recovery_observations_to_recovery_insight():
    observations = (
        _observation(
            AthleteObservationType.HRV_BELOW_BASELINE,
            "health-day-1:hrv",
            confidence=0.9,
        ),
        _observation(
            AthleteObservationType.SLEEP_DEBT,
            "health-day-1:sleep",
        ),
    )
    original_observations = observations

    insights = InsightBuilder().build(observations)

    assert len(insights) == 1
    insight = insights[0]
    assert insight.id == "need_more_recovery:health-day-1:hrv:health-day-1:sleep"
    assert insight.type is AthleteInsightType.NEED_MORE_RECOVERY
    assert insight.confidence == 0.9
    assert insight.evidence == ("health-day-1:hrv", "health-day-1:sleep")
    assert insight.as_of == datetime(2026, 7, 1, 8)
    assert observations == original_observations


def test_builder_is_deterministic_when_no_rule_has_sufficient_evidence():
    observations = (
        _observation(AthleteObservationType.SLEEP_DEBT, "health-day-1"),
        _observation(
            AthleteObservationType.HRV_BELOW_BASELINE,
            "health-day-2",
            observed_at=datetime(2026, 7, 2, 8),
        ),
    )

    assert InsightBuilder().build(observations) == ()
    assert InsightBuilder().build(observations) == InsightBuilder().build(observations)
