from datetime import datetime, timedelta

from athlete.intelligence.models import (
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
)
from athlete.intelligence.rules import ComplianceRule, FatigueRule, RecoveryRule
from athlete.memory.models import WorkoutMemoryObservation


def _workout(
    event_id: str,
    *,
    day: int,
    planned_tss: float = 100.0,
    executed_tss: float = 100.0,
    completion_score: float = 95.0,
    completed: bool = True,
) -> WorkoutMemoryObservation:
    return WorkoutMemoryObservation(
        event_id=event_id,
        occurred_at=datetime(2026, 7, day, 8),
        planned_duration=60.0,
        executed_duration=60.0,
        planned_tss=planned_tss,
        executed_tss=executed_tss,
        completion_score=completion_score,
        execution_score=completion_score,
        feedback_status="completed",
        completed=completed,
    )


def _observation(
    observation_type: AthleteObservationType,
    evidence: str,
    *,
    observed_at: datetime = datetime(2026, 7, 1, 8),
    confidence: float = 1.0,
) -> AthleteObservation:
    return AthleteObservation(
        id=f"{observation_type.value}:{evidence}",
        type=observation_type,
        value=1.0,
        confidence=confidence,
        observed_at=observed_at,
        evidence=(evidence,),
    )


def test_fatigue_rule_detects_two_consecutive_high_load_workouts():
    history = (
        _workout("event-1", day=1, executed_tss=116.0),
        _workout("event-2", day=2, executed_tss=120.0),
    )
    observations = tuple(
        _observation(AthleteObservationType.TRAINING_LOAD_HIGH, workout.event_id)
        for workout in history
    )

    insight = FatigueRule().evaluate(observations, history)

    assert insight is not None
    assert insight.type is AthleteInsightType.FATIGUE_ACCUMULATING
    assert insight.evidence == ("event-1", "event-2")
    assert insight.as_of == datetime(2026, 7, 2, 8)


def test_fatigue_rule_rejects_high_load_workouts_separated_by_a_normal_workout():
    history = (
        _workout("event-1", day=1, executed_tss=116.0),
        _workout("event-2", day=2),
        _workout("event-3", day=3, executed_tss=116.0),
    )
    observations = (
        _observation(AthleteObservationType.TRAINING_LOAD_HIGH, "event-1"),
        _observation(AthleteObservationType.TRAINING_LOAD_HIGH, "event-3"),
    )

    assert FatigueRule().evaluate(observations, history) is None


def test_fatigue_rule_excludes_the_115_percent_load_boundary_and_is_deterministic():
    history = (
        _workout("event-1", day=1, executed_tss=115.0),
        _workout("event-2", day=2, executed_tss=116.0),
    )
    observations = tuple(
        _observation(AthleteObservationType.TRAINING_LOAD_HIGH, workout.event_id)
        for workout in history
    )

    assert FatigueRule().evaluate(observations, history) is None
    assert FatigueRule().evaluate(observations, history) == FatigueRule().evaluate(
        observations,
        history,
    )


def test_recovery_rule_requires_hrv_and_sleep_observations_at_the_same_moment():
    observed_at = datetime(2026, 7, 1, 8)
    observations = (
        _observation(
            AthleteObservationType.HRV_BELOW_BASELINE,
            "health-day-1:hrv",
            observed_at=observed_at,
            confidence=0.8,
        ),
        _observation(
            AthleteObservationType.SLEEP_DEBT,
            "health-day-1:sleep",
            observed_at=observed_at,
            confidence=0.9,
        ),
    )

    insight = RecoveryRule().evaluate(observations, ())

    assert insight is not None
    assert insight.type is AthleteInsightType.NEED_MORE_RECOVERY
    assert insight.confidence == 0.8
    assert insight.evidence == ("health-day-1:hrv", "health-day-1:sleep")
    assert insight.as_of == observed_at


def test_recovery_rule_rejects_observations_from_different_moments():
    observations = (
        _observation(AthleteObservationType.HRV_BELOW_BASELINE, "hrv"),
        _observation(
            AthleteObservationType.SLEEP_DEBT,
            "sleep",
            observed_at=datetime(2026, 7, 2, 8),
        ),
    )

    assert RecoveryRule().evaluate(observations, ()) is None


def test_compliance_rule_detects_three_completed_workouts_at_the_score_boundary():
    history = (
        _workout("event-1", day=1, completion_score=90.0),
        _workout("event-2", day=2, completion_score=95.0),
        _workout("event-3", day=3, completion_score=100.0),
    )

    insight = ComplianceRule().evaluate((), history)

    assert insight is not None
    assert insight.type is AthleteInsightType.HIGH_TRAINING_COMPLIANCE
    assert insight.evidence == ("event-1", "event-2", "event-3")
    assert insight.as_of == datetime(2026, 7, 3, 8)


def test_compliance_rule_rejects_too_little_history_or_any_low_execution():
    insufficient_history = (
        _workout("event-1", day=1),
        _workout("event-2", day=2),
    )
    incomplete_history = (
        _workout("event-1", day=1),
        _workout("event-2", day=2, completion_score=89.99),
        _workout("event-3", day=3),
    )

    assert ComplianceRule().evaluate((), insufficient_history) is None
    assert ComplianceRule().evaluate((), incomplete_history) is None


def test_compliance_rule_respects_execution_low_observation_and_does_not_mutate_inputs():
    history = (
        _workout("event-1", day=1),
        _workout("event-2", day=2),
        _workout("event-3", day=3),
    )
    observations = (
        _observation(AthleteObservationType.EXECUTION_LOW, "event-2"),
    )
    original_history = history
    original_observations = observations

    assert ComplianceRule().evaluate(observations, history) is None
    assert history == original_history
    assert observations == original_observations
