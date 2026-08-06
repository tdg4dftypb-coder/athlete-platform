from dataclasses import dataclass
from enum import Enum, auto
from biomarkers.trends.models import BiomarkerTrend


class Interpretation(Enum):
    UNKNOWN = auto()
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()


class ConfidenceLevel(Enum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass(frozen=True)
class BiomarkerInsight:
    canonical_code: str
    interpretation: Interpretation
    confidence: ConfidenceLevel
    summary: str | None
    reasoning: str | None
    trend: BiomarkerTrend
