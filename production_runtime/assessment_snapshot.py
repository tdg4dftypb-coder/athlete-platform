"""Immutable operational recovery artifact for one runtime assessment input."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from typing import Protocol, runtime_checkable

from morning_briefing.input_models import (
    BiomarkerBriefingInput,
    BiomarkerBriefingSignalInput,
    MorningBriefingInput,
    RecoveryBriefingInput,
    TrainingBriefingInput,
)


ASSESSMENT_SNAPSHOT_SCHEMA_VERSION = "1.0"


class AssessmentSnapshotError(RuntimeError):
    pass


class AssessmentSnapshotMissingError(AssessmentSnapshotError):
    pass


class AssessmentSnapshotConflictError(AssessmentSnapshotError):
    pass


class AssessmentSnapshotIntegrityError(AssessmentSnapshotError):
    pass


class AssessmentSnapshotUnavailableError(AssessmentSnapshotError):
    pass


def _aware_utc(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must use UTC")


@dataclass(frozen=True)
class AssessmentSnapshot:
    runtime_id: str
    target_local_date: date
    created_at_utc: datetime
    input: MorningBriefingInput
    artifact_id: str
    schema_version: str = ASSESSMENT_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_id, str) or not self.runtime_id.strip():
            raise ValueError("runtime_id must be non-empty")
        if type(self.target_local_date) is not date:
            raise TypeError("target_local_date must be a date")
        _aware_utc(self.created_at_utc, "created_at_utc")
        if not isinstance(self.input, MorningBriefingInput):
            raise TypeError("input must be MorningBriefingInput")
        _aware_utc(self.input.generated_at, "input.generated_at")
        if self.schema_version != ASSESSMENT_SNAPSHOT_SCHEMA_VERSION:
            raise ValueError(f"unsupported snapshot schema_version '{self.schema_version}'")
        expected = AssessmentSnapshotCodec.artifact_id_for(self.input)
        if self.artifact_id != expected:
            raise AssessmentSnapshotIntegrityError("assessment snapshot content hash mismatch")


class AssessmentSnapshotCodec:
    """Canonical JSON codec for the minimal runtime-consumed briefing input."""

    SCHEMA_VERSION = ASSESSMENT_SNAPSHOT_SCHEMA_VERSION

    @classmethod
    def canonical_input_payload(cls, value: MorningBriefingInput) -> str:
        data = {
            "schema_version": cls.SCHEMA_VERSION,
            "generated_at": value.generated_at.isoformat(),
            "recovery": cls._recovery(value.recovery),
            "training": cls._training(value.training),
            "biomarkers": cls._biomarkers(value.biomarkers),
        }
        return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def artifact_id_for(cls, value: MorningBriefingInput) -> str:
        digest = sha256(cls.canonical_input_payload(value).encode("utf-8")).hexdigest()
        return f"assessment:sha256:{digest}"

    def encode(self, snapshot: AssessmentSnapshot) -> str:
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "runtime_id": snapshot.runtime_id,
            "target_local_date": snapshot.target_local_date.isoformat(),
            "created_at_utc": snapshot.created_at_utc.isoformat(),
            "artifact_id": snapshot.artifact_id,
            "input": json.loads(self.canonical_input_payload(snapshot.input)),
        }
        return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def decode(self, payload: str) -> AssessmentSnapshot:
        try:
            data = json.loads(payload)
            if data["schema_version"] != self.SCHEMA_VERSION:
                raise AssessmentSnapshotIntegrityError(
                    f"unsupported assessment snapshot schema_version '{data['schema_version']}'"
                )
            raw = data["input"]
            if raw["schema_version"] != self.SCHEMA_VERSION:
                raise AssessmentSnapshotIntegrityError("invalid assessment input schema version")
            value = MorningBriefingInput(
                generated_at=datetime.fromisoformat(raw["generated_at"]),
                recovery=self._decode_recovery(raw.get("recovery")),
                training=self._decode_training(raw.get("training")),
                biomarkers=self._decode_biomarkers(raw.get("biomarkers")),
            )
            return AssessmentSnapshot(
                runtime_id=data["runtime_id"],
                target_local_date=date.fromisoformat(data["target_local_date"]),
                created_at_utc=datetime.fromisoformat(data["created_at_utc"]),
                input=value,
                artifact_id=data["artifact_id"],
                schema_version=data["schema_version"],
            )
        except AssessmentSnapshotIntegrityError:
            raise
        except Exception as error:
            raise AssessmentSnapshotIntegrityError("malformed assessment snapshot payload") from error

    @staticmethod
    def _recovery(value):
        return None if value is None else {
            "score": value.score, "status": value.status, "summary": value.summary,
            "is_stale": value.is_stale, "hrv_status": value.hrv_status,
            "resting_heart_rate_status": value.resting_heart_rate_status,
            "sleep_status": value.sleep_status,
        }

    @staticmethod
    def _training(value):
        return None if value is None else {
            "title": value.title, "description": value.description,
            "duration_minutes": value.duration_minutes, "intensity": value.intensity,
            "is_available": value.is_available, "session_type": value.session_type,
            "recent_training_load": value.recent_training_load,
            "fatigue_status": value.fatigue_status,
        }

    @staticmethod
    def _biomarkers(value):
        return None if value is None else {
            "available_count": value.available_count,
            "attention_count": value.attention_count,
            "summary": value.summary, "is_stale": value.is_stale,
            "critical_count": value.critical_count,
            "signals": [
                {"canonical_code": item.canonical_code, "interpretation": item.interpretation,
                 "data_quality": item.data_quality, "summary": item.summary}
                for item in value.signals
            ],
            "data_status": value.data_status,
        }

    @staticmethod
    def _decode_recovery(value):
        return None if value is None else RecoveryBriefingInput(**value)

    @staticmethod
    def _decode_training(value):
        return None if value is None else TrainingBriefingInput(**value)

    @staticmethod
    def _decode_biomarkers(value):
        if value is None:
            return None
        copy = dict(value)
        copy["signals"] = tuple(BiomarkerBriefingSignalInput(**item) for item in value["signals"])
        return BiomarkerBriefingInput(**copy)


@runtime_checkable
class AssessmentSnapshotRepository(Protocol):
    def save(self, snapshot: AssessmentSnapshot) -> None: ...
    def get_by_runtime_id(self, runtime_id: str) -> AssessmentSnapshot | None: ...
    def get_by_artifact_id(self, artifact_id: str) -> AssessmentSnapshot | None: ...
