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
