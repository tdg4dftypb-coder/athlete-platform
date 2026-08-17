"""Canonical pure serialization for Athlete Context Memory v2."""
from __future__ import annotations

from datetime import datetime
import json

from athlete.context_memory.models import (
    MemoryAttribute,
    MemoryConfidence,
    MemoryDomain,
    MemoryItem,
    MemoryKind,
    MemoryOrigin,
    MemoryProvenance,
    MemorySensitivity,
    MemoryStatus,
    MemoryValue,
)


class MemoryItemCodec:
    SCHEMA_VERSION = "1.0"

    def encode(self, item: MemoryItem) -> str:
        if not isinstance(item, MemoryItem):
            raise TypeError("item must be MemoryItem")
        data = self._semantic_data(item)
        data.update(
            {
                "schema_version": self.SCHEMA_VERSION,
                "memory_id": item.memory_id,
                "status": item.status.value,
                "recorded_at": item.recorded_at.isoformat(),
            }
        )
        return self._json(data)

    def encode_semantics(self, item: MemoryItem) -> str:
        if not isinstance(item, MemoryItem):
            raise TypeError("item must be MemoryItem")
        return self._json(self._semantic_data(item))

    def decode(self, value: str) -> MemoryItem:
        if not isinstance(value, str):
            raise TypeError("serialized memory item must be a string")
        data = json.loads(value)
        if not isinstance(data, dict) or data.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("unsupported context memory schema version")
        payload = data["payload"]
        provenance = data["provenance"]
        return MemoryItem(
            memory_id=data["memory_id"],
            subject_id=data["subject_id"],
            kind=MemoryKind(data["kind"]),
            domain=MemoryDomain(data["domain"]),
            payload=MemoryValue(
                key=payload["key"],
                value=payload["value"],
                attributes=tuple(
                    MemoryAttribute(key=item["key"], value=item["value"])
                    for item in payload["attributes"]
                ),
            ),
            origin=MemoryOrigin(data["origin"]),
            status=MemoryStatus(data["status"]),
            sensitivity=MemorySensitivity(data["sensitivity"]),
            provenance=MemoryProvenance(
                source_type=provenance["source_type"],
                source_ref=provenance["source_ref"],
                evidence_refs=tuple(provenance["evidence_refs"]),
                inference_rule_version=provenance["inference_rule_version"],
            ),
            confidence=(
                None
                if data["confidence"] is None
                else MemoryConfidence(data["confidence"])
            ),
            recorded_at=datetime.fromisoformat(data["recorded_at"]),
            observed_at=(
                None
                if data["observed_at"] is None
                else datetime.fromisoformat(data["observed_at"])
            ),
            valid_from=datetime.fromisoformat(data["valid_from"]),
            valid_until=(
                None
                if data["valid_until"] is None
                else datetime.fromisoformat(data["valid_until"])
            ),
            supersedes_memory_id=data["supersedes_memory_id"],
        )

    @staticmethod
    def _semantic_data(item: MemoryItem) -> dict:
        return {
            "subject_id": item.subject_id,
            "kind": item.kind.value,
            "domain": item.domain.value,
            "payload": item.payload.canonical_data(),
            "origin": item.origin.value,
            "sensitivity": item.sensitivity.value,
            "provenance": item.provenance.canonical_data(),
            "confidence": None if item.confidence is None else item.confidence.value,
            "observed_at": (
                None if item.observed_at is None else item.observed_at.isoformat()
            ),
            "valid_from": item.valid_from.isoformat(),
            "valid_until": (
                None if item.valid_until is None else item.valid_until.isoformat()
            ),
            "supersedes_memory_id": item.supersedes_memory_id,
        }

    @staticmethod
    def _json(data: dict) -> str:
        return json.dumps(
            data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
