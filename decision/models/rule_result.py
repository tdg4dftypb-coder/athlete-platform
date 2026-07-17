from dataclasses import dataclass

from workout.enums import WorkoutType


@dataclass(frozen=True)
class RuleResult:
    source: str
    scores: dict[WorkoutType, float]
    reason: str