"""Deterministic Stage 31.3 write policy; no conversational extraction."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256

from athlete.context_memory.models import (
    MemoryItem,
    MemoryKind,
    MemoryOrigin,
    MemorySensitivity,
)
from training.ingestion.source_identity import SourceIdentity


class MemoryWriteMode(str, Enum):
    AUTO = "AUTO"
    EXPLICIT = "EXPLICIT"
    EPHEMERAL = "EPHEMERAL"


class MemoryWriteDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_EXPLICIT_AUTHORIZATION = "REQUIRE_EXPLICIT_AUTHORIZATION"
    REJECT = "REJECT"


class MemoryWriteReason(str, Enum):
    ALLOWED_EXPLICIT = "ALLOWED_EXPLICIT"
    ALLOWED_SYSTEM_COMMITMENT = "ALLOWED_SYSTEM_COMMITMENT"
    ALLOWED_LEARNED_PATTERN = "ALLOWED_LEARNED_PATTERN"
    EXPLICIT_AUTHORIZATION_REQUIRED = "EXPLICIT_AUTHORIZATION_REQUIRED"
    SENSITIVE_INFERENCE_FORBIDDEN = "SENSITIVE_INFERENCE_FORBIDDEN"
    UNAPPROVED_SYSTEM_SOURCE = "UNAPPROVED_SYSTEM_SOURCE"
    UNAPPROVED_INFERENCE_SOURCE = "UNAPPROVED_INFERENCE_SOURCE"
    EPHEMERAL_CONTEXT_FORBIDDEN = "EPHEMERAL_CONTEXT_FORBIDDEN"
    AUTO_STORE_FORBIDDEN = "AUTO_STORE_FORBIDDEN"
    SOURCE_MISMATCH = "SOURCE_MISMATCH"


def _utc(name: str, value: datetime) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must use UTC")


@dataclass(frozen=True)
class MemoryWriteRequest:
    item: MemoryItem
    mode: MemoryWriteMode
    source_identity: SourceIdentity
    requested_at: datetime
    explicit_authorized: bool = False
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.item, MemoryItem):
            raise TypeError("item must be MemoryItem")
        if not isinstance(self.mode, MemoryWriteMode):
            raise TypeError("mode must be MemoryWriteMode")
        if not isinstance(self.source_identity, SourceIdentity):
            raise TypeError("source_identity must be SourceIdentity")
        _utc("requested_at", self.requested_at)
        if not isinstance(self.explicit_authorized, bool):
            raise TypeError("explicit_authorized must be bool")
        if self.reason is not None:
            if not isinstance(self.reason, str) or not self.reason.strip():
                raise ValueError("reason must be non-empty when provided")
            if len(self.reason) > 256:
                raise ValueError("reason exceeds maximum length 256")

    @property
    def action_identity(self) -> str:
        raw = f"{self.source_identity.provider}|{self.source_identity.external_id}"
        return "action:sha256:" + sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryLifecycleRequest:
    memory_id: str
    source_identity: SourceIdentity
    requested_at: datetime
    explicit_authorized: bool

    def __post_init__(self) -> None:
        if not isinstance(self.memory_id, str) or not self.memory_id.strip():
            raise ValueError("memory_id must be non-empty")
        if not isinstance(self.source_identity, SourceIdentity):
            raise TypeError("source_identity must be SourceIdentity")
        _utc("requested_at", self.requested_at)
        if not isinstance(self.explicit_authorized, bool):
            raise TypeError("explicit_authorized must be bool")

    @property
    def action_identity(self) -> str:
        raw = f"{self.source_identity.provider}|{self.source_identity.external_id}"
        return "action:sha256:" + sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryWritePolicyResult:
    decision: MemoryWriteDecision
    reason: MemoryWriteReason


class DeterministicMemoryWritePolicy:
    """Narrow allowlist for automatic durable memory writes."""

    DEFAULT_SYSTEM_SOURCES = frozenset({"coach_commitment_service"})
    DEFAULT_INFERENCE_SOURCES = frozenset({"approved_memory_inference"})

    def __init__(
        self,
        *,
        approved_system_sources: frozenset[str] | None = None,
        approved_inference_sources: frozenset[str] | None = None,
    ) -> None:
        self._system_sources = (
            self.DEFAULT_SYSTEM_SOURCES
            if approved_system_sources is None
            else approved_system_sources
        )
        self._inference_sources = (
            self.DEFAULT_INFERENCE_SOURCES
            if approved_inference_sources is None
            else approved_inference_sources
        )

    def evaluate(self, request: MemoryWriteRequest) -> MemoryWritePolicyResult:
        item = request.item
        provider = request.source_identity.provider
        if provider != item.provenance.source_type:
            return self._reject(MemoryWriteReason.SOURCE_MISMATCH)
        if request.mode is MemoryWriteMode.EPHEMERAL:
            return self._reject(MemoryWriteReason.EPHEMERAL_CONTEXT_FORBIDDEN)
        if item.sensitivity is MemorySensitivity.SENSITIVE:
            if item.origin is MemoryOrigin.INFERRED:
                return self._reject(MemoryWriteReason.SENSITIVE_INFERENCE_FORBIDDEN)
            if not request.explicit_authorized:
                return self._require()

        if item.kind is MemoryKind.COMMITMENT:
            if provider not in self._system_sources:
                return self._reject(MemoryWriteReason.UNAPPROVED_SYSTEM_SOURCE)
            if request.mode is MemoryWriteMode.AUTO:
                return self._allow(MemoryWriteReason.ALLOWED_SYSTEM_COMMITMENT)

        if item.kind is MemoryKind.LEARNED_PATTERN:
            if provider not in self._inference_sources:
                return self._reject(MemoryWriteReason.UNAPPROVED_INFERENCE_SOURCE)
            if request.mode is MemoryWriteMode.AUTO:
                return self._allow(MemoryWriteReason.ALLOWED_LEARNED_PATTERN)

        if request.mode is MemoryWriteMode.AUTO:
            return self._require()
        if request.mode is MemoryWriteMode.EXPLICIT and request.explicit_authorized:
            return self._allow(MemoryWriteReason.ALLOWED_EXPLICIT)
        return self._require()

    @staticmethod
    def _allow(reason: MemoryWriteReason) -> MemoryWritePolicyResult:
        return MemoryWritePolicyResult(MemoryWriteDecision.ALLOW, reason)

    @staticmethod
    def _require() -> MemoryWritePolicyResult:
        return MemoryWritePolicyResult(
            MemoryWriteDecision.REQUIRE_EXPLICIT_AUTHORIZATION,
            MemoryWriteReason.EXPLICIT_AUTHORIZATION_REQUIRED,
        )

    @staticmethod
    def _reject(reason: MemoryWriteReason) -> MemoryWritePolicyResult:
        return MemoryWritePolicyResult(MemoryWriteDecision.REJECT, reason)
