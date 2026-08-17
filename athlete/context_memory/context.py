"""Bounded durable-memory-only context assembly for future Stage 32 use."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Protocol

from athlete.context_memory.models import MemoryDomain, MemoryItem, MemoryKind
from athlete.context_memory.retrieval import (
    CoachMemoryItem,
    MemoryRetrievalRequest,
    MemoryRetrievalResult,
    validate_utc,
)


MAX_COACH_MEMORY_ITEMS = 32
CATEGORY_LIMITS = {
    MemoryKind.PREFERENCE: 8,
    MemoryKind.CONSTRAINT: 8,
    MemoryKind.GOAL: 4,
    MemoryKind.COMMITMENT: 6,
    MemoryKind.LEARNED_PATTERN: 4,
    MemoryKind.CORRECTION: 4,
}
TRUNCATION_PRIORITY = (
    MemoryKind.CONSTRAINT,
    MemoryKind.GOAL,
    MemoryKind.CORRECTION,
    MemoryKind.COMMITMENT,
    MemoryKind.PREFERENCE,
    MemoryKind.LEARNED_PATTERN,
)


class CoachMemoryLimitation(str, Enum):
    MEMORY_CONTEXT_TRUNCATED = "MEMORY_CONTEXT_TRUNCATED"
    SENSITIVE_MEMORY_EXCLUDED = "SENSITIVE_MEMORY_EXCLUDED"
    INCONSISTENT_ACTIVE_MEMORY = "INCONSISTENT_ACTIVE_MEMORY"
    NO_ACTIVE_MEMORY = "NO_ACTIVE_MEMORY"


class ContextMemoryReadPort(Protocol):
    def retrieve(self, request: MemoryRetrievalRequest) -> MemoryRetrievalResult:
        ...


@dataclass(frozen=True)
class CoachMemoryContextRequest:
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


@dataclass(frozen=True)
class CoachMemoryContext:
    subject_id: str
    as_of: datetime
    active_preferences: tuple[CoachMemoryItem, ...]
    active_constraints: tuple[CoachMemoryItem, ...]
    active_goals: tuple[CoachMemoryItem, ...]
    active_commitments: tuple[CoachMemoryItem, ...]
    relevant_learned_patterns: tuple[CoachMemoryItem, ...]
    recent_corrections: tuple[CoachMemoryItem, ...]
    source_memory_ids: tuple[str, ...]
    limitations: tuple[CoachMemoryLimitation, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        validate_utc("as_of", self.as_of)
        categories = {
            MemoryKind.PREFERENCE: self.active_preferences,
            MemoryKind.CONSTRAINT: self.active_constraints,
            MemoryKind.GOAL: self.active_goals,
            MemoryKind.COMMITMENT: self.active_commitments,
            MemoryKind.LEARNED_PATTERN: self.relevant_learned_patterns,
            MemoryKind.CORRECTION: self.recent_corrections,
        }
        all_items = []
        for kind, values in categories.items():
            if not isinstance(values, tuple) or any(
                not isinstance(item, CoachMemoryItem) for item in values
            ):
                raise TypeError("context categories must contain CoachMemoryItem values")
            if len(values) > CATEGORY_LIMITS[kind]:
                raise ValueError(f"{kind.value} category exceeds its bound")
            if any(item.kind is not kind for item in values):
                raise ValueError(f"{kind.value} category contains wrong kind")
            all_items.extend(values)
        if len(all_items) > MAX_COACH_MEMORY_ITEMS:
            raise ValueError("CoachMemoryContext exceeds global item bound")
        expected_ids = tuple(item.memory_id for item in all_items)
        if self.source_memory_ids != expected_ids:
            raise ValueError("source_memory_ids must match projected category order")
        if len(set(self.source_memory_ids)) != len(self.source_memory_ids):
            raise ValueError("CoachMemoryContext contains duplicate memory IDs")
        if not self.fingerprint.startswith("coach-memory-context:sha256:"):
            raise ValueError("invalid CoachMemoryContext fingerprint")


class CoachMemoryContextBuilder:
    def __init__(self, repository: ContextMemoryReadPort) -> None:
        self._repository = repository

    def build(self, request: CoachMemoryContextRequest) -> CoachMemoryContext:
        if not isinstance(request, CoachMemoryContextRequest):
            raise TypeError("request must be CoachMemoryContextRequest")
        results: dict[MemoryKind, MemoryRetrievalResult] = {}
        for kind in TRUNCATION_PRIORITY:
            if request.kinds and kind not in request.kinds:
                results[kind] = MemoryRetrievalResult((), False, False)
                continue
            results[kind] = self._repository.retrieve(
                MemoryRetrievalRequest(
                    subject_id=request.subject_id,
                    as_of=request.as_of,
                    kinds=(kind,),
                    domains=request.domains,
                    limit=CATEGORY_LIMITS[kind],
                    include_sensitive=request.include_sensitive,
                )
            )

        limitations: set[CoachMemoryLimitation] = set()
        if any(result.truncated for result in results.values()):
            limitations.add(CoachMemoryLimitation.MEMORY_CONTEXT_TRUNCATED)
        if any(result.sensitive_excluded for result in results.values()):
            limitations.add(CoachMemoryLimitation.SENSITIVE_MEMORY_EXCLUDED)

        ordered = [
            (kind, item)
            for kind in TRUNCATION_PRIORITY
            for item in results[kind].items
        ]
        inconsistent_ids = self._inconsistent_ids(tuple(item for _, item in ordered))
        if inconsistent_ids:
            limitations.add(CoachMemoryLimitation.INCONSISTENT_ACTIVE_MEMORY)
            ordered = [pair for pair in ordered if pair[1].memory_id not in inconsistent_ids]
        if len(ordered) > MAX_COACH_MEMORY_ITEMS:
            limitations.add(CoachMemoryLimitation.MEMORY_CONTEXT_TRUNCATED)
            ordered = ordered[:MAX_COACH_MEMORY_ITEMS]

        projected: dict[MemoryKind, list[CoachMemoryItem]] = {
            kind: [] for kind in TRUNCATION_PRIORITY
        }
        for kind, item in ordered:
            projected[kind].append(
                CoachMemoryItem.from_item(
                    item, sensitive_authorized=request.include_sensitive
                )
            )
        if not ordered:
            limitations.add(CoachMemoryLimitation.NO_ACTIVE_MEMORY)

        preferences = tuple(projected[MemoryKind.PREFERENCE])
        constraints = tuple(projected[MemoryKind.CONSTRAINT])
        goals = tuple(projected[MemoryKind.GOAL])
        commitments = tuple(projected[MemoryKind.COMMITMENT])
        learned = tuple(projected[MemoryKind.LEARNED_PATTERN])
        corrections = tuple(projected[MemoryKind.CORRECTION])
        source_ids = tuple(
            item.memory_id
            for values in (preferences, constraints, goals, commitments, learned, corrections)
            for item in values
        )
        ordered_limitations = tuple(
            value for value in CoachMemoryLimitation if value in limitations
        )
        fingerprint = self._fingerprint(
            request.subject_id,
            request.as_of,
            (preferences, constraints, goals, commitments, learned, corrections),
            ordered_limitations,
        )
        return CoachMemoryContext(
            subject_id=request.subject_id,
            as_of=request.as_of,
            active_preferences=preferences,
            active_constraints=constraints,
            active_goals=goals,
            active_commitments=commitments,
            relevant_learned_patterns=learned,
            recent_corrections=corrections,
            source_memory_ids=source_ids,
            limitations=ordered_limitations,
            fingerprint=fingerprint,
        )

    @staticmethod
    def _inconsistent_ids(items: tuple[MemoryItem, ...]) -> set[str]:
        by_id = {item.memory_id: item for item in items}
        children: dict[str, list[MemoryItem]] = {}
        inconsistent: set[str] = set()
        for item in items:
            parent = item.supersedes_memory_id
            if parent is None:
                continue
            children.setdefault(parent, []).append(item)
            if parent in by_id:
                inconsistent.update((parent, item.memory_id))
        for values in children.values():
            if len(values) > 1:
                inconsistent.update(item.memory_id for item in values)
        return inconsistent

    @staticmethod
    def _fingerprint(subject_id, as_of, categories, limitations) -> str:
        def projection_data(item: CoachMemoryItem) -> dict:
            return {
                "memory_id": item.memory_id,
                "kind": item.kind.value,
                "domain": item.domain.value,
                "value": item.value.canonical_data(),
                "origin": item.origin.value,
                "confidence": None if item.confidence is None else item.confidence.value,
                "valid_from": item.valid_from.isoformat(),
                "sensitivity": item.sensitivity.value,
                "source_type": item.source_type,
                "source_ref": item.source_ref,
                "evidence_refs": list(item.evidence_refs),
                "inference_rule_version": item.inference_rule_version,
            }

        payload = {
            "subject_id": subject_id,
            "as_of": as_of.isoformat(),
            "categories": [
                [projection_data(item) for item in category]
                for category in categories
            ],
            "limitations": [item.value for item in limitations],
        }
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return "coach-memory-context:sha256:" + sha256(
            canonical.encode("utf-8")
        ).hexdigest()
