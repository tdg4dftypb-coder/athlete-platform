from uuid import uuid4

from athlete.memory.models import (
    AthleteMemoryEvent,
    AthleteMemoryEventType,
)
from athlete.memory.repository import (
    AthleteMemoryRepository,
    DuplicateSourceIdentityError,
)
from athlete.memory.serializer import WorkoutCompletedSerializer
from pipeline.models import PostWorkoutResult
from training.ingestion.source_identity import SourceIdentity


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
        source_identity: SourceIdentity,
    ) -> AthleteMemoryEvent:

        existing = self.repository.get_by_source_identity(
            AthleteMemoryEventType.WORKOUT_COMPLETED,
            source_identity.provider,
            source_identity.external_id,
        )
        if existing is not None:
            return existing

        event = AthleteMemoryEvent(
            event_id=str(uuid4()),
            occurred_at=result.activity.end,
            event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
            source_type=source_identity.provider,
            source_key=source_identity.external_id,
            schema_version=self.serializer.SCHEMA_VERSION,
            payload=self.serializer.serialize(result),
        )

        try:
            self.repository.append(event)
        except DuplicateSourceIdentityError:
            existing = self.repository.get_by_source_identity(
                AthleteMemoryEventType.WORKOUT_COMPLETED,
                source_identity.provider,
                source_identity.external_id,
            )
            if existing is None:
                raise
            return existing

        return event
