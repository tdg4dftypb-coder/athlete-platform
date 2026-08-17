from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    ALREADY_MATCHED = "ALREADY_MATCHED"


class MatchMethod(str, Enum):
    CANONICAL = "CANONICAL"
    EXACT_LINK = "EXACT_LINK"
    DETERMINISTIC_CANDIDATE = "DETERMINISTIC_CANDIDATE"


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    NEVER_SYNCED = "NEVER_SYNCED"


@dataclass(frozen=True)
class SourceActivityObservation:
    provider: str
    external_id: str
    sport: str
    start_at: datetime
    end_at: datetime
    distance_meters: float | None = None
    linked_provider: str | None = None
    linked_external_id: str | None = None

    def __post_init__(self):
        if self.provider not in {"zwift_fit", "intervals_icu", "healthkit"}:
            raise ValueError("unsupported provider")
        if not self.external_id or not self.sport:
            raise ValueError("identity and sport are required")
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.end_at < self.start_at:
            raise ValueError("end precedes start")

    @property
    def duration_seconds(self):
        return (self.end_at - self.start_at).total_seconds()


def canonical_activity_id(provider: str, external_id: str) -> str:
    digest = sha256(f"{provider}\0{external_id}".encode()).hexdigest()
    return f"activity:{digest}"


@dataclass(frozen=True)
class ActivityAlias:
    provider: str
    external_id: str
    match_method: MatchMethod
    evidence: str


@dataclass(frozen=True)
class CanonicalActivityGroup:
    canonical_activity_id: str
    canonical_provider: str
    canonical_external_id: str
    aliases: tuple[ActivityAlias, ...]
    reconciled_at: datetime


@dataclass(frozen=True)
class SourceReconciliationResult:
    provider: str
    external_id: str
    status: ReconciliationStatus
    canonical_activity_id: str | None
    match_method: MatchMethod | None
    evidence: str


@dataclass(frozen=True)
class ProviderFreshness:
    provider: str
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    watermark: str | None
    operational_status: str
    last_error_code: str | None

    def state(self, now: datetime, target_seconds: int) -> FreshnessState:
        if self.last_success_at is None:
            return FreshnessState.NEVER_SYNCED
        if self.operational_status == "DISABLED":
            return FreshnessState.UNAVAILABLE
        return (FreshnessState.FRESH if (now - self.last_success_at).total_seconds() <= target_seconds
                else FreshnessState.STALE)
