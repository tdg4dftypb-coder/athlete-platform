from athlete.intelligence.models import (
    AthleteObservation,
    AthleteObservationType,
    HealthObservationInput,
)
from athlete.memory.models import AthleteMemorySnapshot, WorkoutMemoryObservation


class ObservationProjector:
    """Projects typed training observations from an already-read Memory snapshot."""

    HIGH_TRAINING_LOAD_RATIO = 1.15
    HRV_BELOW_BASELINE_DELTA_PERCENT = -5.0
    HRV_ABOVE_BASELINE_DELTA_PERCENT = 5.0
    SLEEP_DEBT_MINUTES = 60.0
    RECOVERY_GOOD_MINIMUM_SCORE = 85.0

    def project(
        self,
        snapshot: AthleteMemorySnapshot | None = None,
        health: HealthObservationInput | None = None,
    ) -> tuple[AthleteObservation, ...]:
        observations = []

        if snapshot is not None:
            for workout in snapshot.workout_observations:
                observation = self._low_execution_observation(workout)
                if observation is not None:
                    observations.append(observation)

                observation = self._high_training_load_observation(workout)
                if observation is not None:
                    observations.append(observation)

        if health is not None:
            observations.extend(self._health_observations(health))

        return tuple(observations)

    def _health_observations(
        self,
        health: HealthObservationInput,
    ) -> tuple[AthleteObservation, ...]:
        observations = []

        if health.hrv_delta_percent is not None:
            if health.hrv_delta_percent <= self.HRV_BELOW_BASELINE_DELTA_PERCENT:
                observations.append(
                    self._health_observation(
                        AthleteObservationType.HRV_BELOW_BASELINE,
                        health.hrv_delta_percent,
                        health,
                    )
                )
            elif health.hrv_delta_percent >= self.HRV_ABOVE_BASELINE_DELTA_PERCENT:
                observations.append(
                    self._health_observation(
                        AthleteObservationType.HRV_ABOVE_BASELINE,
                        health.hrv_delta_percent,
                        health,
                    )
                )

        if (
            health.sleep_duration_minutes is not None
            and health.sleep_baseline_minutes is not None
            and health.sleep_duration_minutes
            <= health.sleep_baseline_minutes - self.SLEEP_DEBT_MINUTES
        ):
            observations.append(
                self._health_observation(
                    AthleteObservationType.SLEEP_DEBT,
                    health.sleep_baseline_minutes - health.sleep_duration_minutes,
                    health,
                )
            )

        if (
            health.recovery_score is not None
            and health.recovery_score >= self.RECOVERY_GOOD_MINIMUM_SCORE
        ):
            observations.append(
                self._health_observation(
                    AthleteObservationType.RECOVERY_GOOD,
                    health.recovery_score,
                    health,
                )
            )

        return tuple(observations)

    @staticmethod
    def _health_observation(
        observation_type: AthleteObservationType,
        value: float,
        health: HealthObservationInput,
    ) -> AthleteObservation:
        return AthleteObservation(
            id=f"{observation_type.value}:{health.observed_at.isoformat()}",
            type=observation_type,
            value=value,
            confidence=1.0,
            observed_at=health.observed_at,
            evidence=health.evidence,
        )

    @staticmethod
    def _low_execution_observation(
        workout: WorkoutMemoryObservation,
    ) -> AthleteObservation | None:
        if workout.completed:
            return None

        return AthleteObservation(
            id=f"{AthleteObservationType.EXECUTION_LOW.value}:{workout.event_id}",
            type=AthleteObservationType.EXECUTION_LOW,
            value=workout.execution_score,
            confidence=1.0,
            observed_at=workout.occurred_at,
            evidence=(workout.event_id,),
        )

    def _high_training_load_observation(
        self,
        workout: WorkoutMemoryObservation,
    ) -> AthleteObservation | None:
        if workout.planned_tss <= 0:
            return None

        load_ratio = workout.executed_tss / workout.planned_tss
        if load_ratio <= self.HIGH_TRAINING_LOAD_RATIO:
            return None

        return AthleteObservation(
            id=(
                f"{AthleteObservationType.TRAINING_LOAD_HIGH.value}:"
                f"{workout.event_id}"
            ),
            type=AthleteObservationType.TRAINING_LOAD_HIGH,
            value=load_ratio,
            confidence=1.0,
            observed_at=workout.occurred_at,
            evidence=(workout.event_id,),
        )
