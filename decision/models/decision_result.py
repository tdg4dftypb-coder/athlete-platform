from dataclasses import dataclass, field

from decision.prescription.models import TrainingObjective
from decision.sports import Sport
from workout.enums import WorkoutType


@dataclass
class DecisionResult:

    sport: Sport

    recommendation: WorkoutType

    duration: int

    target_tss: float

    intensity: str

    reasons: list[str]

    objective: TrainingObjective | None = None

    priority: int = 100

    confidence: float = 100.0

    source_rules: list[str] = field(
        default_factory=list,
    )