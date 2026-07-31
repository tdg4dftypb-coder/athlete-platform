from datetime import datetime, timedelta

import pytest

from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
    DateRange,
)
from athlete.memory.reader import AthleteMemoryReader


class FakeAthleteMemoryRepository:

    def __init__(self, events: list[AthleteMemoryEvent]) -> None:

        self.events = events
        self.requested_period: tuple[datetime, datetime] | None = None

    def load_between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[AthleteMemoryEvent]:

        self.requested_period = (start, end)
        return self.events


def build_event(
    event_id: str,
    occurred_at: datetime,
    *,
    event_type: AthleteMemoryEventType | str = AthleteMemoryEventType.WORKOUT_COMPLETED,
    schema_version: int = 1,
    payload: dict | None = None,
) -> AthleteMemoryEvent:

    payload = payload or {
        "schema_version": schema_version,
        "execution": {
            "planned_duration": 60,
            "executed_duration": 55,
            "planned_tss": 80,
            "executed_tss": 75,
            "completion_score": 90,
            "execution_score": 88,
            "completed": True,
        },
        "feedback": {"status": "completed"},
    }

    return AthleteMemoryEvent(
        event_id=event_id,
        occurred_at=occurred_at,
        event_type=event_type,
        source_type="activity",
        source_key=f"activity-{event_id}",
        schema_version=schema_version,
        payload=payload,
    )


def test_reader_returns_empty_snapshot_for_empty_range():

    start = datetime(2026, 8, 1, 8, 0)
    period = DateRange(start=start, end=start + timedelta(days=1))
    repository = FakeAthleteMemoryRepository([])

    snapshot = AthleteMemoryReader(repository).read(period)

    assert snapshot.period == period
    assert snapshot.workout_observations == ()
    assert snapshot.source_event_ids == ()
    assert snapshot.schema_version == 1
    assert repository.requested_period == (period.start, period.end)


def test_date_range_rejects_equal_start_and_end():

    moment = datetime(2026, 8, 1, 8, 0)

    with pytest.raises(ValueError, match="end must be after start"):
        DateRange(start=moment, end=moment)


def test_date_range_rejects_end_before_start():

    start = datetime(2026, 8, 1, 8, 0)

    with pytest.raises(ValueError, match="end must be after start"):
        DateRange(start=start, end=start - timedelta(seconds=1))


def test_reader_projects_a_single_workout_completed_event():

    start = datetime(2026, 8, 1, 8, 0)
    event = build_event("event-1", start)
    period = DateRange(start=start, end=start + timedelta(days=1))

    snapshot = AthleteMemoryReader(FakeAthleteMemoryRepository([event])).read(period)

    assert len(snapshot.workout_observations) == 1
    assert snapshot.workout_observations[0].event_id == event.event_id
    assert snapshot.workout_observations[0].executed_tss == 75
    assert snapshot.workout_observations[0].feedback_status == "completed"
    assert snapshot.source_event_ids == (event.event_id,)


def test_reader_ignores_unknown_additive_payload_fields():

    start = datetime(2026, 8, 1, 8, 0)
    event = build_event(
        "event-with-extra-fields",
        start,
        payload={
            "schema_version": 1,
            "execution": {
                "planned_duration": 60,
                "executed_duration": 55,
                "planned_tss": 80,
                "executed_tss": 75,
                "completion_score": 90,
                "execution_score": 88,
                "completed": True,
                "future_execution_field": "ignored",
            },
            "feedback": {
                "status": "completed",
                "future_feedback_field": "ignored",
            },
            "future_payload_section": {"value": "ignored"},
        },
    )
    period = DateRange(start=start, end=start + timedelta(days=1))

    snapshot = AthleteMemoryReader(FakeAthleteMemoryRepository([event])).read(period)

    observation = snapshot.workout_observations[0]
    assert observation.event_id == event.event_id
    assert observation.executed_tss == 75
    assert observation.feedback_status == "completed"


def test_reader_returns_observations_in_chronological_order():

    start = datetime(2026, 8, 1, 8, 0)
    events = [
        build_event("later", start + timedelta(hours=2)),
        build_event("earlier", start),
        build_event("middle", start + timedelta(hours=1)),
    ]
    period = DateRange(start=start, end=start + timedelta(days=1))

    snapshot = AthleteMemoryReader(FakeAthleteMemoryRepository(events)).read(period)

    assert [observation.event_id for observation in snapshot.workout_observations] == [
        "earlier",
        "middle",
        "later",
    ]
    assert snapshot.source_event_ids == ("earlier", "middle", "later")


def test_reader_includes_the_start_of_the_period():

    start = datetime(2026, 8, 1, 8, 0)
    event = build_event("at-start", start)
    period = DateRange(start=start, end=start + timedelta(days=1))

    snapshot = AthleteMemoryReader(FakeAthleteMemoryRepository([event])).read(period)

    assert snapshot.source_event_ids == ("at-start",)


def test_reader_excludes_the_end_of_the_period():

    start = datetime(2026, 8, 1, 8, 0)
    end = start + timedelta(days=1)
    event = build_event("at-end", end)
    period = DateRange(start=start, end=end)

    snapshot = AthleteMemoryReader(FakeAthleteMemoryRepository([event])).read(period)

    assert snapshot.workout_observations == ()
    assert snapshot.source_event_ids == ()


def test_reader_rejects_unsupported_event_type():

    start = datetime(2026, 8, 1, 8, 0)
    event = build_event("unsupported", start, event_type="health_updated")
    period = DateRange(start=start, end=start + timedelta(days=1))

    with pytest.raises(ValueError, match="Unsupported athlete memory event type"):
        AthleteMemoryReader(FakeAthleteMemoryRepository([event])).read(period)


def test_reader_rejects_unsupported_schema_version():

    start = datetime(2026, 8, 1, 8, 0)
    event = build_event("future", start, schema_version=2)
    period = DateRange(start=start, end=start + timedelta(days=1))

    with pytest.raises(ValueError, match="Unsupported athlete memory schema version"):
        AthleteMemoryReader(FakeAthleteMemoryRepository([event])).read(period)


def test_reader_rejects_invalid_workout_completed_payload():

    start = datetime(2026, 8, 1, 8, 0)
    event = build_event(
        "invalid-payload",
        start,
        payload={"schema_version": 1, "execution": {}},
    )
    period = DateRange(start=start, end=start + timedelta(days=1))

    with pytest.raises(ValueError, match="Invalid workout completed event payload"):
        AthleteMemoryReader(FakeAthleteMemoryRepository([event])).read(period)
