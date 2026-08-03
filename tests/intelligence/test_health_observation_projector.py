from datetime import datetime

from athlete.intelligence.models import AthleteObservationType, HealthObservationInput
from athlete.intelligence.observation_projector import ObservationProjector
from athlete.intelligence.rules import RecoveryRule


def _health_input(
    *,
    hrv_delta_percent: float | None = None,
    sleep_duration_minutes: float | None = None,
    sleep_baseline_minutes: float | None = None,
    recovery_score: float | None = None,
) -> HealthObservationInput:
    return HealthObservationInput(
        observed_at=datetime(2026, 7, 1, 8),
        hrv_delta_percent=hrv_delta_percent,
        sleep_duration_minutes=sleep_duration_minutes,
        sleep_baseline_minutes=sleep_baseline_minutes,
        recovery_score=recovery_score,
        evidence=("health-day-1",),
    )


def test_projector_emits_hrv_below_baseline_at_the_existing_warning_boundary():
    observations = ObservationProjector().project(
        health=_health_input(hrv_delta_percent=-5.0),
    )

    assert len(observations) == 1
    assert observations[0].type is AthleteObservationType.HRV_BELOW_BASELINE
    assert observations[0].value == -5.0
    assert observations[0].evidence == ("health-day-1",)


def test_projector_emits_hrv_above_baseline_at_the_existing_improvement_boundary():
    observations = ObservationProjector().project(
        health=_health_input(hrv_delta_percent=5.0),
    )

    assert len(observations) == 1
    assert observations[0].type is AthleteObservationType.HRV_ABOVE_BASELINE
    assert observations[0].value == 5.0


def test_projector_ignores_hrv_inside_the_neutral_range_and_when_missing():
    assert ObservationProjector().project(
        health=_health_input(hrv_delta_percent=-4.99),
    ) == ()
    assert ObservationProjector().project(health=_health_input()) == ()


def test_projector_emits_sleep_debt_at_a_sixty_minute_deficit():
    observations = ObservationProjector().project(
        health=_health_input(
            sleep_duration_minutes=360.0,
            sleep_baseline_minutes=420.0,
        ),
    )

    assert len(observations) == 1
    assert observations[0].type is AthleteObservationType.SLEEP_DEBT
    assert observations[0].value == 60.0


def test_projector_ignores_sleep_deficit_below_boundary_and_missing_sleep_data():
    assert ObservationProjector().project(
        health=_health_input(
            sleep_duration_minutes=360.01,
            sleep_baseline_minutes=420.0,
        ),
    ) == ()
    assert ObservationProjector().project(
        health=_health_input(sleep_duration_minutes=360.0),
    ) == ()


def test_projector_emits_recovery_good_at_existing_recovery_threshold():
    observations = ObservationProjector().project(
        health=_health_input(recovery_score=85.0),
    )

    assert len(observations) == 1
    assert observations[0].type is AthleteObservationType.RECOVERY_GOOD
    assert observations[0].value == 85.0


def test_projector_ignores_recovery_below_threshold_and_missing_data():
    assert ObservationProjector().project(
        health=_health_input(recovery_score=84.99),
    ) == ()
    assert ObservationProjector().project(health=_health_input()) == ()


def test_projector_accepts_each_input_independently_and_is_deterministic():
    health = _health_input(
        hrv_delta_percent=-5.0,
        sleep_duration_minutes=360.0,
        sleep_baseline_minutes=420.0,
        recovery_score=85.0,
    )

    observations = ObservationProjector().project(health=health)

    assert [observation.type for observation in observations] == [
        AthleteObservationType.HRV_BELOW_BASELINE,
        AthleteObservationType.SLEEP_DEBT,
        AthleteObservationType.RECOVERY_GOOD,
    ]
    assert ObservationProjector().project() == ()
    assert ObservationProjector().project(health=health) == observations


def test_recovery_rule_uses_actual_health_observations_from_projector():
    health = _health_input(
        hrv_delta_percent=-5.0,
        sleep_duration_minutes=360.0,
        sleep_baseline_minutes=420.0,
    )
    observations = ObservationProjector().project(health=health)

    insight = RecoveryRule().evaluate(observations, ())

    assert insight is not None
    assert insight.type.value == "need_more_recovery"
    assert insight.evidence == ("health-day-1",)
    assert insight.as_of == health.observed_at
