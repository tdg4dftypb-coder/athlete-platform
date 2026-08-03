from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class AthleteGoalType(Enum):
    MAINTAIN = "maintain"
    REDUCE_BODY_MASS = "reduce_body_mass"


class GoalAssessmentDataStatus(Enum):
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
