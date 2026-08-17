from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json


class SourceTrust(str, Enum):
    HIGH_FIDELITY = "HIGH_FIDELITY"


@dataclass(frozen=True)
class CanonicalActivityCandidate:
    provider: str
    external_id: str
    start_at: datetime
    end_at: datetime
    duration_seconds: int | None
    sport: str | None
    distance_meters: float | None
    normalized_power: float | None
    intensity_factor: float | None
    tss: float | None
    artifact_fingerprint: str
    artifact_reference: str
    ingested_at: datetime
    trust: SourceTrust = SourceTrust.HIGH_FIDELITY

    def __post_init__(self):
        if self.provider != "zwift_fit":
            raise ValueError("Zwift candidate provider must be zwift_fit")
        for value in (self.start_at, self.end_at, self.ingested_at):
            if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
                raise ValueError("candidate timestamps must be UTC")
        if self.end_at < self.start_at:
            raise ValueError("candidate end precedes start")
        if "/" in self.artifact_reference or "\\" in self.artifact_reference:
            raise ValueError("artifact reference must not expose a path")

    def serialize(self) -> dict:
        value = asdict(self)
        value["start_at"] = self.start_at.isoformat()
        value["end_at"] = self.end_at.isoformat()
        value["ingested_at"] = self.ingested_at.isoformat()
        value["trust"] = self.trust.value
        return value

    @property
    def fingerprint(self) -> str:
        raw = json.dumps(self.serialize(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class ArtifactFailure:
    artifact_reference: str
    code: str


@dataclass(frozen=True)
class ZwiftFitSyncResult:
    discovered: int
    ready: int
    ingested: int
    duplicate: int
    skipped_not_stable: int
    malformed: int
    failed: int
    started_at: datetime
    completed_at: datetime
    candidates: tuple[CanonicalActivityCandidate, ...]
    failures: tuple[ArtifactFailure, ...]
