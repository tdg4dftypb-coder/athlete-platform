"""Pure domain contracts for durable Athlete Context Memory v2."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
import re
from typing import Any


DEFAULT_SUBJECT_ID = "athlete:primary"
MAX_EVIDENCE_REFS = 16
MAX_ATTRIBUTES = 8
MAX_KEY_LENGTH = 64
MAX_TEXT_VALUE_LENGTH = 512
MAX_ATTRIBUTE_TEXT_LENGTH = 256
MAX_PAYLOAD_BYTES = 2048

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_MEMORY_ID_PATTERN = re.compile(r"^memory:sha256:[0-9a-f]{64}$")
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {"conversation", "conversation_history", "messages", "raw_conversation", "transcript"}
)


class MemoryKind(str, Enum):
    PREFERENCE = "PREFERENCE"
    CONSTRAINT = "CONSTRAINT"
    GOAL = "GOAL"
    CORRECTION = "CORRECTION"
    COMMITMENT = "COMMITMENT"
    LEARNED_PATTERN = "LEARNED_PATTERN"


class MemoryDomain(str, Enum):
    TRAINING = "TRAINING"
    RECOVERY = "RECOVERY"
    HEALTH = "HEALTH"
    LIFESTYLE = "LIFESTYLE"
    EQUIPMENT = "EQUIPMENT"
    NUTRITION = "NUTRITION"


class MemoryOrigin(str, Enum):
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
    SYSTEM = "SYSTEM"


class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    FORGOTTEN = "FORGOTTEN"


class MemorySensitivity(str, Enum):
    NORMAL = "NORMAL"
    SENSITIVE = "SENSITIVE"


class MemoryConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


ScalarValue = str | int | float | bool


def _non_empty(name: str, value: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds maximum length {maximum}")
    return value


def _key(name: str, value: str) -> str:
    _non_empty(name, value, maximum=MAX_KEY_LENGTH)
    if not _KEY_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a canonical lowercase key")
    if value in _FORBIDDEN_PAYLOAD_KEYS:
        raise ValueError(f"{name} cannot represent conversation transcript data")
    return value


def _scalar(name: str, value: ScalarValue, *, text_limit: int) -> ScalarValue:
    if isinstance(value, str):
        return _non_empty(name, value, maximum=text_limit)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float) and isfinite(value):
        return value
    raise TypeError(f"{name} must be a bounded string, bool, int, or finite float")


def _utc(name: str, value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must use UTC")
    return value


@dataclass(frozen=True)
class MemoryAttribute:
    key: str
    value: ScalarValue

    def __post_init__(self) -> None:
        _key("attribute key", self.key)
        _scalar("attribute value", self.value, text_limit=MAX_ATTRIBUTE_TEXT_LENGTH)

    def canonical_data(self) -> dict[str, Any]:
        return {"key": self.key, "value": self.value}


@dataclass(frozen=True)
class MemoryValue:
    """Bounded typed value; deliberately cannot hold arbitrary JSON or transcripts."""

    key: str
    value: ScalarValue
    attributes: tuple[MemoryAttribute, ...] = ()

    def __post_init__(self) -> None:
        _key("payload key", self.key)
        _scalar("payload value", self.value, text_limit=MAX_TEXT_VALUE_LENGTH)
        if not isinstance(self.attributes, tuple):
            raise TypeError("attributes must be a tuple")
        if len(self.attributes) > MAX_ATTRIBUTES:
            raise ValueError(f"attributes cannot contain more than {MAX_ATTRIBUTES} entries")
        if any(not isinstance(item, MemoryAttribute) for item in self.attributes):
            raise TypeError("attributes must contain MemoryAttribute values")
        if len({item.key for item in self.attributes}) != len(self.attributes):
            raise ValueError("attributes must have unique keys")
        canonical = tuple(sorted(self.attributes, key=lambda item: item.key))
        object.__setattr__(self, "attributes", canonical)
        if len(self.canonical_json().encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"payload exceeds maximum size {MAX_PAYLOAD_BYTES} bytes")

    def canonical_data(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "attributes": [item.canonical_data() for item in self.attributes],
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_data(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )


@dataclass(frozen=True)
class MemoryProvenance:
    source_type: str
    source_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    inference_rule_version: str | None = None

    def __post_init__(self) -> None:
        _key("source_type", self.source_type)
        if self.source_ref is not None:
            _non_empty("source_ref", self.source_ref, maximum=256)
        if not isinstance(self.evidence_refs, tuple):
            raise TypeError("evidence_refs must be a tuple")
        if len(self.evidence_refs) > MAX_EVIDENCE_REFS:
            raise ValueError(
                f"evidence_refs cannot contain more than {MAX_EVIDENCE_REFS} entries"
            )
        for reference in self.evidence_refs:
            _non_empty("evidence_ref", reference, maximum=256)
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be unique")
        object.__setattr__(self, "evidence_refs", tuple(sorted(self.evidence_refs)))
        if self.inference_rule_version is not None:
            _non_empty(
                "inference_rule_version", self.inference_rule_version, maximum=64
            )

    def canonical_data(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "evidence_refs": list(self.evidence_refs),
            "inference_rule_version": self.inference_rule_version,
        }


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    subject_id: str
    kind: MemoryKind
    domain: MemoryDomain
    payload: MemoryValue
    origin: MemoryOrigin
    status: MemoryStatus
    sensitivity: MemorySensitivity
    provenance: MemoryProvenance
    confidence: MemoryConfidence | None
    recorded_at: datetime
    valid_from: datetime
    observed_at: datetime | None = None
    valid_until: datetime | None = None
    supersedes_memory_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MemoryKind):
            raise TypeError("kind must be MemoryKind")
        if not isinstance(self.domain, MemoryDomain):
            raise TypeError("domain must be MemoryDomain")
        if not isinstance(self.payload, MemoryValue):
            raise TypeError("payload must be MemoryValue")
        if not isinstance(self.origin, MemoryOrigin):
            raise TypeError("origin must be MemoryOrigin")
        if not isinstance(self.status, MemoryStatus):
            raise TypeError("status must be MemoryStatus")
        if not isinstance(self.sensitivity, MemorySensitivity):
            raise TypeError("sensitivity must be MemorySensitivity")
        if not isinstance(self.provenance, MemoryProvenance):
            raise TypeError("provenance must be MemoryProvenance")
        _non_empty("subject_id", self.subject_id, maximum=128)
        _utc("recorded_at", self.recorded_at)
        _utc("valid_from", self.valid_from)
        if self.observed_at is not None:
            _utc("observed_at", self.observed_at)
            if self.observed_at > self.recorded_at:
                raise ValueError("observed_at cannot be after recorded_at")
        if self.valid_until is not None:
            _utc("valid_until", self.valid_until)
            if self.valid_until <= self.valid_from:
                raise ValueError("valid_until must be after valid_from")
        if self.supersedes_memory_id is not None:
            self._validate_memory_id("supersedes_memory_id", self.supersedes_memory_id)
            if self.supersedes_memory_id == self.memory_id:
                raise ValueError("memory item cannot supersede itself")

        self._validate_origin()
        self._validate_kind()
        self._validate_memory_id("memory_id", self.memory_id)
        if self.memory_id != self.identity_for(
            subject_id=self.subject_id,
            kind=self.kind,
            domain=self.domain,
            payload=self.payload,
            origin=self.origin,
            sensitivity=self.sensitivity,
            provenance=self.provenance,
            confidence=self.confidence,
            observed_at=self.observed_at,
            valid_from=self.valid_from,
            valid_until=self.valid_until,
            supersedes_memory_id=self.supersedes_memory_id,
        ):
            raise ValueError("memory_id does not match canonical item semantics")

    def _validate_origin(self) -> None:
        inferred = self.origin is MemoryOrigin.INFERRED
        if inferred:
            if self.confidence is None:
                raise ValueError("INFERRED memory requires confidence")
            if not isinstance(self.confidence, MemoryConfidence):
                raise TypeError("confidence must be MemoryConfidence")
            if not self.provenance.evidence_refs:
                raise ValueError("INFERRED memory requires evidence_refs")
            if self.provenance.inference_rule_version is None:
                raise ValueError("INFERRED memory requires inference_rule_version")
        else:
            if self.confidence is not None:
                raise ValueError("confidence is allowed only for INFERRED memory")
            if self.provenance.inference_rule_version is not None:
                raise ValueError("inference_rule_version is allowed only for INFERRED memory")

    def _validate_kind(self) -> None:
        if self.kind is MemoryKind.LEARNED_PATTERN:
            if self.origin is not MemoryOrigin.INFERRED:
                raise ValueError("LEARNED_PATTERN must be INFERRED")
            if len(self.provenance.evidence_refs) < 2:
                raise ValueError("LEARNED_PATTERN requires at least two evidence_refs")
        if self.kind is MemoryKind.CORRECTION:
            if self.origin is not MemoryOrigin.EXPLICIT:
                raise ValueError("CORRECTION must be EXPLICIT")
            if self.supersedes_memory_id is None:
                raise ValueError("CORRECTION must reference a superseded memory item")
        if self.kind is MemoryKind.COMMITMENT and self.origin is not MemoryOrigin.SYSTEM:
            raise ValueError("COMMITMENT must be SYSTEM-originated")

    @staticmethod
    def _validate_memory_id(name: str, value: str) -> None:
        if not isinstance(value, str) or not _MEMORY_ID_PATTERN.fullmatch(value):
            raise ValueError(f"{name} must use memory:sha256:<64 lowercase hex>")

    @classmethod
    def create(
        cls,
        *,
        kind: MemoryKind,
        domain: MemoryDomain,
        payload: MemoryValue,
        origin: MemoryOrigin,
        sensitivity: MemorySensitivity,
        provenance: MemoryProvenance,
        recorded_at: datetime,
        valid_from: datetime,
        subject_id: str = DEFAULT_SUBJECT_ID,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        confidence: MemoryConfidence | None = None,
        observed_at: datetime | None = None,
        valid_until: datetime | None = None,
        supersedes_memory_id: str | None = None,
    ) -> "MemoryItem":
        memory_id = cls.identity_for(
            subject_id=subject_id,
            kind=kind,
            domain=domain,
            payload=payload,
            origin=origin,
            sensitivity=sensitivity,
            provenance=provenance,
            confidence=confidence,
            observed_at=observed_at,
            valid_from=valid_from,
            valid_until=valid_until,
            supersedes_memory_id=supersedes_memory_id,
        )
        return cls(
            memory_id=memory_id,
            subject_id=subject_id,
            kind=kind,
            domain=domain,
            payload=payload,
            origin=origin,
            status=status,
            sensitivity=sensitivity,
            provenance=provenance,
            confidence=confidence,
            recorded_at=recorded_at,
            observed_at=observed_at,
            valid_from=valid_from,
            valid_until=valid_until,
            supersedes_memory_id=supersedes_memory_id,
        )

    @staticmethod
    def identity_for(
        *,
        subject_id: str,
        kind: MemoryKind,
        domain: MemoryDomain,
        payload: MemoryValue,
        origin: MemoryOrigin,
        sensitivity: MemorySensitivity,
        provenance: MemoryProvenance,
        confidence: MemoryConfidence | None,
        observed_at: datetime | None,
        valid_from: datetime,
        valid_until: datetime | None,
        supersedes_memory_id: str | None,
    ) -> str:
        data = {
            "subject_id": subject_id,
            "kind": kind.value,
            "domain": domain.value,
            "payload": payload.canonical_data(),
            "origin": origin.value,
            "sensitivity": sensitivity.value,
            "provenance": provenance.canonical_data(),
            "confidence": None if confidence is None else confidence.value,
            "observed_at": None if observed_at is None else observed_at.isoformat(),
            "valid_from": valid_from.isoformat(),
            "valid_until": None if valid_until is None else valid_until.isoformat(),
            "supersedes_memory_id": supersedes_memory_id,
        }
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "memory:sha256:" + sha256(canonical.encode("utf-8")).hexdigest()

    def is_active(self, as_of: datetime) -> bool:
        _utc("as_of", as_of)
        return (
            self.status is MemoryStatus.ACTIVE
            and self.valid_from <= as_of
            and (self.valid_until is None or as_of < self.valid_until)
        )

    def transition_to(self, status: MemoryStatus) -> "MemoryItem":
        if not isinstance(status, MemoryStatus):
            raise TypeError("status must be MemoryStatus")
        legal = {
            MemoryStatus.SUPERSEDED,
            MemoryStatus.REVOKED,
            MemoryStatus.FORGOTTEN,
        }
        if self.status is not MemoryStatus.ACTIVE or status not in legal:
            raise ValueError(f"illegal memory lifecycle transition: {self.status.value} -> {status.value}")
        return replace(self, status=status)


@dataclass(frozen=True)
class ForgottenMemoryTombstone:
    """Non-sensitive lifecycle marker; original payload and evidence are absent."""

    memory_id: str
    subject_id: str
    forgotten_at: datetime

    def __post_init__(self) -> None:
        MemoryItem._validate_memory_id("memory_id", self.memory_id)
        _non_empty("subject_id", self.subject_id, maximum=128)
        _utc("forgotten_at", self.forgotten_at)
