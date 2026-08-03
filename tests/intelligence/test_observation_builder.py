from datetime import datetime, timedelta

from athlete.intelligence.models import AthleteObservationType
from athlete.intelligence.observation_projector import ObservationProjector
from athlete.memory.models import (
    AthleteMemorySnapshot,
    DateRange,
    WorkoutMemoryObservation,
)


def _snapshot(*workouts: WorkoutMemoryObservation) -> AthleteMemorySnapshot:
    start = datetime(2026, 7, 1)
    return AthleteMemorySnapshot(
        period=DateRange(start=start, end=start + timedelta(days=7)),
        workout_observations=workouts,
        source_event_ids=tuple(workout.event_id for workout in workouts),
        schema_version=1,
    )


def _workout(
    event_id: str,
    *,
    completed: bool = True,
    execution_score: float = 95.0,
    planned_tss: float = 100.0,
    executed_tss: float = 100.0,
) -> WorkoutMemoryObservation:
    return WorkoutMemoryObservation(
        event_id=event_id,
        occurred_at=datetime(2026, 7, 2, 8),
        planned_duration=60.0,
        executed_duration=60.0,
        planned_tss=planned_tss,
        executed_tss=executed_tss,
        completion_score=execution_score,
        execution_score=execution_score,
        feedback_status="completed",
        completed=completed,
    )


def test_builder_maps_incomplete_execution_to_a_deterministic_observation():
    snapshot = _snapshot(_workout("event-1", completed=False, execution_score=70.0))
    original_snapshot = snapshot

    observations = ObservationProjector().project(snapshot)

    assert len(observations) == 1
    assert observations[0].id == "execution_low:event-1"
    assert observations[0].type is AthleteObservationType.EXECUTION_LOW
    assert observations[0].value == 70.0
    assert observations[0].confidence == 1.0
    assert observations[0].evidence == ("event-1",)
    assert observations[0].observed_at == datetime(2026, 7, 2, 8)
    assert ObservationProjector().project(snapshot) == observations
    assert snapshot == original_snapshot


def test_builder_maps_load_above_the_existing_over_execution_boundary():
    snapshot = _snapshot(_workout("event-2", executed_tss=116.0))

    observations = ObservationProjector().project(snapshot)

    assert len(observations) == 1
    observation = observations[0]
    assert observation.id == "training_load_high:event-2"
    assert observation.type is AthleteObservationType.TRAINING_LOAD_HIGH
    assert observation.value == 1.16
    assert observation.confidence == 1.0
    assert observation.evidence == ("event-2",)


def test_builder_does_not_infer_observations_not_supported_by_memory_snapshot():
    snapshot = _snapshot(
        _workout("event-1"),
        _workout("event-2", planned_tss=0.0, executed_tss=200.0),
    )

    assert ObservationProjector().project(snapshot) == ()


def test_builder_excludes_the_existing_high_load_boundary():
    snapshot = _snapshot(_workout("event-1", executed_tss=115.0))

    assert ObservationProjector().project(snapshot) == ()
