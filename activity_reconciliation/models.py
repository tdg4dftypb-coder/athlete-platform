"""Immutable Stage 28 activity reconciliation contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class MatchStatus(Enum):
    MATCHED = "MATCHED"
    UNMATCHED_PLANNED = "UNMATCHED_PLANNED"
    UNMATCHED_ACTIVITY = "UNMATCHED_ACTIVITY"
    AMBIGUOUS = "AMBIGUOUS"


class ActivityExecutionOutcome(Enum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    SKIPPED = "SKIPPED"
    REPLACED = "REPLACED"
    UNPLANNED = "UNPLANNED"


@dataclass(frozen=True)
class ActivityReference:
    event_id: str
    source_type: str
    source_key: str


@dataclass(frozen=True)
class ReplacementEvidence:
    planned_session_id: str
    activity_event_id: str
    source: str
    reason_code: str
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        for name in ("planned_session_id", "activity_event_id", "source", "reason_code"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")


@dataclass(frozen=True)
class ReconciliationItem:
    match_status: MatchStatus
    planned_session_id: str | None = None
    activity: ActivityReference | None = None
    candidate_session_ids: tuple[str, ...] = ()
    candidate_activity_event_ids: tuple[str, ...] = ()
    execution_outcome: ActivityExecutionOutcome | None = None
    completion_percent: float | None = None
    reason_codes: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReconciliationResult:
    reconciliation_id: str
    input_fingerprint: str
    policy_version: str
    target_local_date: date
    timezone_name: str
    plan_id: str
    plan_version: int
    finalized: bool
    planned_session_ids: tuple[str, ...]
    activity_event_ids: tuple[str, ...]
    items: tuple[ReconciliationItem, ...]
    replacement_evidence: tuple[ReplacementEvidence, ...]
    evaluated_at: datetime
