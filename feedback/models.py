from dataclasses import dataclass
from enum import Enum


class WorkoutFeedbackStatus(Enum):
    EXCELLENT = "excellent"
    COMPLETED = "completed"
    PARTIAL = "partial"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class FeedbackSignal:
    code: str
    message: str
    block_name: str | None = None


@dataclass(frozen=True)
class WorkoutFeedback:
    status: WorkoutFeedbackStatus
    headline: str
    summary: str
    execution_score: float
    completion_score: float
    positive_signals: tuple[FeedbackSignal, ...]
    attention_signals: tuple[FeedbackSignal, ...]
