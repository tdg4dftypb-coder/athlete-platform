from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from athlete.intelligence.models import AthleteInsight, AthleteObservation

if TYPE_CHECKING:
    from decision.models import DecisionResult
    from nutrition.models import NutritionAssessment


class RecommendationType(Enum):
    EXTEND_SLEEP = "extend_sleep"
    INCREASE_HYDRATION = "increase_hydration"
    INCREASE_CARBOHYDRATE_INTAKE = "increase_carbohydrate_intake"
    PERFORM_MOBILITY = "perform_mobility"
    LIMIT_ADDITIONAL_ACTIVITY = "limit_additional_activity"
    APPLY_RECOVERY_PROTOCOL = "apply_recovery_protocol"


class RecommendationPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Recommendation:
    id: str
    type: RecommendationType
    priority: RecommendationPriority
    confidence: float
    evidence: tuple[str, ...]
    source_rules: tuple[str, ...]
    as_of: datetime


@dataclass(frozen=True)
class RecommendationResult:
    recommendations: tuple[Recommendation, ...]
    as_of: datetime | None


@dataclass(frozen=True)
class RecommendationContext:
    decision: DecisionResult
    insights: tuple[AthleteInsight, ...]
    observations: tuple[AthleteObservation, ...]
    as_of: datetime | None = None
    nutrition_assessment: NutritionAssessment | None = None
