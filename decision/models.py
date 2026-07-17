from dataclasses import dataclass, field

from decision.sports import Sport


@dataclass
class DecisionState:

    sport: Sport

    recommendation: str

    duration: int

    target_tss: float

    intensity: str

    reasons: list[str]

    priority: int = 100

    confidence: float = 100.0

    source_rules: list[str] = field(default_factory=list)