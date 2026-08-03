from dataclasses import dataclass, field

from .decision_reason import DecisionReason
from .training_objective import TrainingObjective


@dataclass(frozen=True)
class TrainingPrescription:

    objective: TrainingObjective

    duration_minutes: int

    target_tss: int

    priority: int

    confidence: int

    reasons: list[str] = field(default_factory=list)

    decision_reasons: tuple[DecisionReason, ...] = ()
