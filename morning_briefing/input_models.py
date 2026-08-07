from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class RecoveryBriefingInput:
    score: Optional[int]
    status: Optional[str]
    summary: Optional[str]
    is_stale: bool
    hrv_status: Optional[str] = None
    resting_heart_rate_status: Optional[str] = None
    sleep_status: Optional[str] = None


@dataclass(frozen=True)
class TrainingBriefingInput:
    title: Optional[str]
    description: Optional[str]
    duration_minutes: Optional[int]
    intensity: Optional[str]
    is_available: bool


@dataclass(frozen=True)
class BiomarkerBriefingInput:
    available_count: int
    attention_count: int
    summary: Optional[str]
    is_stale: bool


@dataclass(frozen=True)
class MorningBriefingInput:
    generated_at: datetime
    recovery: Optional[RecoveryBriefingInput]
    training: Optional[TrainingBriefingInput]
    biomarkers: Optional[BiomarkerBriefingInput]
