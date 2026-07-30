from dataclasses import dataclass, field

from .readiness import Readiness
from .risk import RiskLevel


@dataclass(frozen=True)
class AthleteDiagnosis:
    readiness: Readiness

    training_capacity: Readiness

    injury_risk: RiskLevel

    confidence: int

    reasons: list[str] = field(default_factory=list)