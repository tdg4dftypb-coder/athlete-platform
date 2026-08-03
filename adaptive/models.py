from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from body_composition.models import BodyCompositionAssessment


class AthleteGoalType(Enum):
    MAINTAIN = "maintain"
    REDUCE_BODY_MASS = "reduce_body_mass"


class GoalAssessmentDataStatus(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"


class BodyMassTrendQualityDataStatus(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class AthleteGoal:
    id: str
    goal_type: AthleteGoalType
    valid_from: date
    recorded_at: datetime
    target_body_mass_kg: float | None = None
    valid_until: date | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoalAssessment:
    """Goal assessment with aggregate completeness metadata.

    ``data_status`` describes completeness of the entire assessment.
    ``confidence`` is a deterministic completeness score, not an estimate of
    accuracy, source quality, or clinical certainty.
    """

    goal: AthleteGoal
    data_status: GoalAssessmentDataStatus
    confidence: float
    valid_for_date: date
    as_of: datetime
    evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class BodyMassTrendQualityInput:
    assessment: BodyCompositionAssessment
    measurement_count: int | None
    source_consistency_known: bool
    valid_for_date: date
    as_of: datetime
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class BodyMassTrendQuality:
    """Completeness of the facts required to interpret a body-mass trend.

    ``confidence`` is a deterministic completeness score, not an estimate of
    measurement accuracy, source quality, or clinical certainty.
    """

    measurement_count: int | None
    period_days: int | None
    current_is_fresh: bool
    baseline_window_valid: bool
    source_consistency_known: bool
    data_status: BodyMassTrendQualityDataStatus
    confidence: float
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    valid_for_date: date
    as_of: datetime
