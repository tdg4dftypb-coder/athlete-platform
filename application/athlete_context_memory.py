"""Stable read-only application boundary for durable athlete memory."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from athlete.context_memory.context import (
    CoachMemoryContext,
    CoachMemoryContextBuilder,
    CoachMemoryContextRequest,
)
from athlete.context_memory.models import MemoryDomain, MemoryKind
from athlete.context_memory.retrieval import validate_utc


COACH_MEMORY_CONTEXT_CONTRACT_VERSION = "1.0"


class AthleteContextMemoryReadError(RuntimeError):
    """A deterministic application-level failure to read durable memory."""


class CoachMemoryContextBuildPort(Protocol):
    def build(self, request: CoachMemoryContextRequest) -> CoachMemoryContext:
        ...


@dataclass(frozen=True)
class CoachMemoryContextQuery:
    """Stage 32-facing query with safe defaults and no repository concerns."""

    subject_id: str
    as_of: datetime
    domains: tuple[MemoryDomain, ...] = ()
    kinds: tuple[MemoryKind, ...] = ()
    include_sensitive: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.subject_id, str) or not self.subject_id.strip():
            raise ValueError("subject_id must be non-empty")
        validate_utc("as_of", self.as_of)
        if not isinstance(self.domains, tuple) or any(
            not isinstance(value, MemoryDomain) for value in self.domains
        ):
            raise TypeError("domains must be a tuple of MemoryDomain")
        if not isinstance(self.kinds, tuple) or any(
            not isinstance(value, MemoryKind) for value in self.kinds
        ):
            raise TypeError("kinds must be a tuple of MemoryKind")
        if len(set(self.domains)) != len(self.domains):
            raise ValueError("domains must be unique")
        if len(set(self.kinds)) != len(self.kinds):
            raise ValueError("kinds must be unique")
        object.__setattr__(self, "domains", tuple(sorted(self.domains, key=lambda x: x.value)))
        object.__setattr__(self, "kinds", tuple(sorted(self.kinds, key=lambda x: x.value)))
        if not isinstance(self.include_sensitive, bool):
            raise TypeError("include_sensitive must be bool")


class AthleteContextMemoryService:
    """Read-only facade; deliberately exposes no memory lifecycle operations."""

    def __init__(self, context_builder: CoachMemoryContextBuildPort) -> None:
        if context_builder is None:
            raise TypeError("context_builder must not be None")
        self._context_builder = context_builder

    def get_coach_memory_context(
        self, query: CoachMemoryContextQuery
    ) -> CoachMemoryContext:
        if not isinstance(query, CoachMemoryContextQuery):
            raise TypeError("query must be CoachMemoryContextQuery")
        request = CoachMemoryContextRequest(
            subject_id=query.subject_id,
            as_of=query.as_of,
            domains=query.domains,
            kinds=query.kinds,
            include_sensitive=query.include_sensitive,
        )
        try:
            return self._context_builder.build(request)
        except AthleteContextMemoryReadError:
            raise
        except Exception as error:
            raise AthleteContextMemoryReadError(
                "durable athlete memory could not be read"
            ) from error


class CoachMemoryContextSerializer:
    """Pure canonical serializer for the Stage 32-facing read contract."""

    def serialize(self, context: CoachMemoryContext) -> dict[str, Any]:
        if not isinstance(context, CoachMemoryContext):
            raise TypeError("context must be CoachMemoryContext")

        def item_data(item) -> dict[str, Any]:
            return {
                "memory_id": item.memory_id,
                "kind": item.kind.value,
                "domain": item.domain.value,
                "value": item.value.canonical_data(),
                "origin": item.origin.value,
                "confidence": None if item.confidence is None else item.confidence.value,
                "valid_from": item.valid_from.isoformat(),
                "sensitivity": item.sensitivity.value,
                "provenance": {
                    "source_type": item.source_type,
                    "source_ref": item.source_ref,
                    "evidence_refs": list(item.evidence_refs),
                    "inference_rule_version": item.inference_rule_version,
                },
            }

        return {
            "contract_version": COACH_MEMORY_CONTEXT_CONTRACT_VERSION,
            "subject_id": context.subject_id,
            "as_of": context.as_of.isoformat(),
            "active_preferences": [item_data(item) for item in context.active_preferences],
            "active_constraints": [item_data(item) for item in context.active_constraints],
            "active_goals": [item_data(item) for item in context.active_goals],
            "active_commitments": [item_data(item) for item in context.active_commitments],
            "relevant_learned_patterns": [
                item_data(item) for item in context.relevant_learned_patterns
            ],
            "recent_corrections": [item_data(item) for item in context.recent_corrections],
            "source_memory_ids": list(context.source_memory_ids),
            "limitations": [value.value for value in context.limitations],
            "fingerprint": context.fingerprint,
        }


def build_athlete_context_memory_service(
    read_port,
) -> AthleteContextMemoryService:
    """Compose the application facade from an injected read port without opening a DB."""

    if read_port is None:
        raise TypeError("read_port must not be None")
    return AthleteContextMemoryService(CoachMemoryContextBuilder(read_port))
