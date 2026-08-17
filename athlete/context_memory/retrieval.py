"""Typed bounded retrieval contracts for durable Context Memory."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from athlete.context_memory.models import (
    MAX_EVIDENCE_REFS,
    MemoryConfidence,
    MemoryDomain,
    MemoryItem,
    MemoryKind,
    MemoryOrigin,
    MemorySensitivity,
    MemoryValue,
)


MAX_RETRIEVAL_ITEMS = 32


def validate_utc(name: str, value: datetime) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must use UTC")


@dataclass(frozen=True)
class MemoryRetrievalRequest:
    subject_id: str
    as_of: datetime
    kinds: tuple[MemoryKind, ...] = ()
    domains: tuple[MemoryDomain, ...] = ()
    limit: int = MAX_RETRIEVAL_ITEMS
    include_sensitive: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.subject_id, str) or not self.subject_id.strip():
            raise ValueError("subject_id must be non-empty")
        validate_utc("as_of", self.as_of)
        if not isinstance(self.kinds, tuple) or any(
            not isinstance(value, MemoryKind) for value in self.kinds
        ):
            raise TypeError("kinds must be a tuple of MemoryKind")
        if not isinstance(self.domains, tuple) or any(
            not isinstance(value, MemoryDomain) for value in self.domains
        ):
            raise TypeError("domains must be a tuple of MemoryDomain")
        if len(set(self.kinds)) != len(self.kinds):
            raise ValueError("kinds must be unique")
        if len(set(self.domains)) != len(self.domains):
            raise ValueError("domains must be unique")
        object.__setattr__(self, "kinds", tuple(sorted(self.kinds, key=lambda x: x.value)))
        object.__setattr__(self, "domains", tuple(sorted(self.domains, key=lambda x: x.value)))
        if not isinstance(self.limit, int) or isinstance(self.limit, bool):
            raise TypeError("limit must be int")
        if not 1 <= self.limit <= MAX_RETRIEVAL_ITEMS:
            raise ValueError(f"limit must be between 1 and {MAX_RETRIEVAL_ITEMS}")
        if not isinstance(self.include_sensitive, bool):
            raise TypeError("include_sensitive must be bool")


@dataclass(frozen=True)
class MemoryRetrievalResult:
    items: tuple[MemoryItem, ...]
    truncated: bool
    sensitive_excluded: bool

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple) or any(
            not isinstance(item, MemoryItem) for item in self.items
        ):
            raise TypeError("items must be a tuple of MemoryItem")
        if len(self.items) > MAX_RETRIEVAL_ITEMS:
            raise ValueError("retrieval result exceeds hard limit")


@dataclass(frozen=True)
class CoachMemoryItem:
    """Coach-facing projection with no persistence or action internals."""

    memory_id: str
    kind: MemoryKind
    domain: MemoryDomain
    value: MemoryValue
    origin: MemoryOrigin
    confidence: MemoryConfidence | None
    valid_from: datetime
    sensitivity: MemorySensitivity
    source_type: str
    source_ref: str | None
    evidence_refs: tuple[str, ...]
    inference_rule_version: str | None

    def __post_init__(self) -> None:
        validate_utc("valid_from", self.valid_from)
        if len(self.evidence_refs) > MAX_EVIDENCE_REFS:
            raise ValueError("projection evidence exceeds domain bound")

    @classmethod
    def from_item(
        cls, item: MemoryItem, *, sensitive_authorized: bool
    ) -> "CoachMemoryItem":
        source_ref = item.provenance.source_ref
        if item.sensitivity is MemorySensitivity.SENSITIVE and not sensitive_authorized:
            source_ref = None
        return cls(
            memory_id=item.memory_id,
            kind=item.kind,
            domain=item.domain,
            value=item.payload,
            origin=item.origin,
            confidence=item.confidence,
            valid_from=item.valid_from,
            sensitivity=item.sensitivity,
            source_type=item.provenance.source_type,
            source_ref=source_ref,
            evidence_refs=item.provenance.evidence_refs,
            inference_rule_version=item.provenance.inference_rule_version,
        )
