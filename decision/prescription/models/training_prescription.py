from dataclasses import dataclass, field

from .training_objective import TrainingObjective


@dataclass(frozen=True)
class TrainingPrescription:

    objective: TrainingObjective

    duration_minutes: int

    target_tss: int

    priority: int

    confidence: int

    reasons: list[str] = field(default_factory=list)