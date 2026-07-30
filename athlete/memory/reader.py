from athlete.memory.models import (
    AthleteMemoryEventType,
    AthleteMemorySnapshot,
    DateRange,
)
from athlete.memory.projector import WorkoutMemoryProjector
from athlete.memory.repository import AthleteMemoryRepository


class AthleteMemoryReader:
    """Builds a typed read-side snapshot from persisted athlete-memory events."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        repository: AthleteMemoryRepository,
        workout_projector: WorkoutMemoryProjector | None = None,
    ) -> None:

        self.repository = repository
        self.workout_projector = workout_projector or WorkoutMemoryProjector()

    def read(
        self,
        period: DateRange,
    ) -> AthleteMemorySnapshot:

        events = self.repository.load_between(period.start, period.end)
        events_in_period = sorted(
            (
                event
                for event in events
                if period.start <= event.occurred_at < period.end
            ),
            key=lambda event: event.occurred_at,
        )

        observations = []
        for event in events_in_period:
            if event.event_type != AthleteMemoryEventType.WORKOUT_COMPLETED:
                raise ValueError(f"Unsupported athlete memory event type: {event.event_type}")
            if event.schema_version != self.SCHEMA_VERSION:
                raise ValueError(
                    f"Unsupported athlete memory schema version: {event.schema_version}"
                )

            observations.append(self.workout_projector.project(event))

        return AthleteMemorySnapshot(
            period=period,
            workout_observations=tuple(observations),
            source_event_ids=tuple(event.event_id for event in events_in_period),
            schema_version=self.SCHEMA_VERSION,
        )
