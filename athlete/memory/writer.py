from uuid import uuid4

from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
)
from athlete.memory.repository import AthleteMemoryRepository
from athlete.memory.serializer import WorkoutCompletedSerializer
from pipeline.models import PostWorkoutResult


class AthleteMemoryWriter:

    def __init__(
        self,
        repository: AthleteMemoryRepository,
        serializer: WorkoutCompletedSerializer | None = None,
    ) -> None:

        self.repository = repository
        self.serializer = serializer or WorkoutCompletedSerializer()

    def write(
        self,
        result: PostWorkoutResult,
    ) -> AthleteMemoryEvent:

        event = AthleteMemoryEvent(
            event_id=str(uuid4()),
            occurred_at=result.activity.end,
            event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
            source_type="activity",
            source_key=result.activity.start.isoformat(),
            schema_version=self.serializer.SCHEMA_VERSION,
            payload=self.serializer.serialize(result),
        )

        self.repository.append(event)

        return event
