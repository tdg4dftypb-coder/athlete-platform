from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class AthleteMemoryEventType(Enum):
    WORKOUT_COMPLETED = "workout_completed"


@dataclass(frozen=True)
class AthleteMemoryEvent:
    event_id: str
    occurred_at: datetime
    event_type: AthleteMemoryEventType
    source_type: str
    source_key: str
    schema_version: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class DateRange:
    """Time range with an inclusive start and exclusive end."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:

        if self.start >= self.end:
            raise ValueError("DateRange end must be after start")


@dataclass(frozen=True)
class WorkoutMemoryObservation:
    event_id: str
    occurred_at: datetime
    planned_duration: float
    executed_duration: float
    planned_tss: float
    executed_tss: float
    completion_score: float
    execution_score: float
    feedback_status: str
    completed: bool


@dataclass(frozen=True)
class AthleteMemorySnapshot:
    period: DateRange
    workout_observations: tuple[WorkoutMemoryObservation, ...]
    source_event_ids: tuple[str, ...]
    schema_version: int
