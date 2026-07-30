from athlete.memory.models import (
    AthleteMemoryEvent,
    WorkoutMemoryObservation,
)


class WorkoutMemoryProjector:
    """Projects a persisted workout-completed event into typed read-side data."""

    def project(
        self,
        event: AthleteMemoryEvent,
    ) -> WorkoutMemoryObservation:

        try:
            payload_schema_version = event.payload["schema_version"]
            execution = event.payload["execution"]
            feedback = event.payload["feedback"]

            if payload_schema_version != event.schema_version:
                raise ValueError("Event and payload schema versions must match")

            return WorkoutMemoryObservation(
                event_id=event.event_id,
                occurred_at=event.occurred_at,
                planned_duration=execution["planned_duration"],
                executed_duration=execution["executed_duration"],
                planned_tss=execution["planned_tss"],
                executed_tss=execution["executed_tss"],
                completion_score=execution["completion_score"],
                execution_score=execution["execution_score"],
                feedback_status=feedback["status"],
                completed=execution["completed"],
            )
        except (KeyError, TypeError) as error:
            raise ValueError("Invalid workout completed event payload") from error
