from typing import Protocol, runtime_checkable

from athlete.intelligence.models import (
    AthleteInsight,
    AthleteInsightType,
    AthleteObservation,
    AthleteObservationType,
)
from athlete.memory.models import WorkoutMemoryObservation


@runtime_checkable
class InsightRule(Protocol):
    """Contract for a future registry of deterministic insight rules."""

    def evaluate(
        self,
        observations: tuple[AthleteObservation, ...],
        workout_history: tuple[WorkoutMemoryObservation, ...],
    ) -> AthleteInsight | None: ...


class FatigueRule:
    """Detects consecutive workouts whose load exceeded the planned load."""

    HIGH_TRAINING_LOAD_RATIO = 1.15

    def evaluate(
        self,
        observations: tuple[AthleteObservation, ...],
        workout_history: tuple[WorkoutMemoryObservation, ...],
    ) -> AthleteInsight | None:
        high_load_event_ids = {
            evidence_id
            for observation in observations
            if observation.type is AthleteObservationType.TRAINING_LOAD_HIGH
            for evidence_id in observation.evidence
        }
        evidence = self._consecutive_high_load_evidence(
            workout_history,
            high_load_event_ids,
        )
        if not evidence:
            return None

        return AthleteInsight(
            id=f"{AthleteInsightType.FATIGUE_ACCUMULATING.value}:{':'.join(evidence)}",
            type=AthleteInsightType.FATIGUE_ACCUMULATING,
            confidence=1.0,
            evidence=evidence,
            as_of=max(
                workout.occurred_at
                for workout in workout_history
                if workout.event_id in evidence
            ),
        )

    def _consecutive_high_load_evidence(
        self,
        workout_history: tuple[WorkoutMemoryObservation, ...],
        high_load_event_ids: set[str],
    ) -> tuple[str, ...]:
        runs = []
        current_run = []

        for workout in workout_history:
            is_high_load = (
                workout.event_id in high_load_event_ids
                and workout.planned_tss > 0
                and workout.executed_tss / workout.planned_tss
                > self.HIGH_TRAINING_LOAD_RATIO
            )
            if is_high_load:
                current_run.append(workout.event_id)
                continue

            if len(current_run) >= 2:
                runs.extend(current_run)
            current_run = []

        if len(current_run) >= 2:
            runs.extend(current_run)

        return tuple(dict.fromkeys(runs))


class RecoveryRule:
    """Detects a same-moment recovery signal from HRV and sleep observations."""

    def evaluate(
        self,
        observations: tuple[AthleteObservation, ...],
        workout_history: tuple[WorkoutMemoryObservation, ...],
    ) -> AthleteInsight | None:
        hrv_by_time = {
            observation.observed_at: observation
            for observation in observations
            if observation.type is AthleteObservationType.HRV_BELOW_BASELINE
        }
        sleep_by_time = {
            observation.observed_at: observation
            for observation in observations
            if observation.type is AthleteObservationType.SLEEP_DEBT
        }
        matching_times = tuple(
            observed_at
            for observed_at in hrv_by_time
            if observed_at in sleep_by_time
        )
        if not matching_times:
            return None

        supporting = tuple(
            observation
            for observation in observations
            if observation.observed_at in matching_times
            and observation.type
            in (
                AthleteObservationType.HRV_BELOW_BASELINE,
                AthleteObservationType.SLEEP_DEBT,
            )
        )
        evidence = self._evidence(supporting)
        return AthleteInsight(
            id=f"{AthleteInsightType.NEED_MORE_RECOVERY.value}:{':'.join(evidence)}",
            type=AthleteInsightType.NEED_MORE_RECOVERY,
            confidence=min(observation.confidence for observation in supporting),
            evidence=evidence,
            as_of=max(matching_times),
        )

    @staticmethod
    def _evidence(
        observations: tuple[AthleteObservation, ...],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                evidence_id
                for observation in observations
                for evidence_id in observation.evidence
            )
        )


class ComplianceRule:
    """Detects consistently completed planned workouts in the supplied history."""

    MINIMUM_WORKOUTS = 3
    MINIMUM_COMPLETION_SCORE = 90.0

    def evaluate(
        self,
        observations: tuple[AthleteObservation, ...],
        workout_history: tuple[WorkoutMemoryObservation, ...],
    ) -> AthleteInsight | None:
        if len(workout_history) < self.MINIMUM_WORKOUTS:
            return None

        low_execution_event_ids = {
            evidence_id
            for observation in observations
            if observation.type is AthleteObservationType.EXECUTION_LOW
            for evidence_id in observation.evidence
        }
        if any(
            not workout.completed
            or workout.completion_score < self.MINIMUM_COMPLETION_SCORE
            or workout.event_id in low_execution_event_ids
            for workout in workout_history
        ):
            return None

        evidence = tuple(workout.event_id for workout in workout_history)
        return AthleteInsight(
            id=(
                f"{AthleteInsightType.HIGH_TRAINING_COMPLIANCE.value}:"
                f"{':'.join(evidence)}"
            ),
            type=AthleteInsightType.HIGH_TRAINING_COMPLIANCE,
            confidence=1.0,
            evidence=evidence,
            as_of=max(workout.occurred_at for workout in workout_history),
        )
