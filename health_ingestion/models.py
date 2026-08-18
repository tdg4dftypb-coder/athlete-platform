"""Strict bounded transport contracts for HealthKit source facts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
import re


HEALTHKIT_CONTRACT_VERSION = "1.0"
MAX_HEALTHKIT_BATCH_RECORDS = 500
MAX_TEXT = 256
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")

SUPPORTED_UNITS = {
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "ms",
    "HKQuantityTypeIdentifierRestingHeartRate": "count/min",
    "HKQuantityTypeIdentifierHeartRate": "count/min",
    "HKQuantityTypeIdentifierBodyMass": "kg",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "kcal",
    "HKQuantityTypeIdentifierBasalEnergyBurned": "kcal",
    "HKQuantityTypeIdentifierStepCount": "count",
    "HKQuantityTypeIdentifierRespiratoryRate": "count/min",
    "HKQuantityTypeIdentifierOxygenSaturation": "fraction",
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature": "degC",
    "HKQuantityTypeIdentifierDistanceCycling": "m",
    "HKQuantityTypeIdentifierCyclingPower": "W",
    "HKQuantityTypeIdentifierCyclingCadence": "count/min",
    "HKCategoryTypeIdentifierSleepAnalysis": "category",
    "HKWorkoutTypeIdentifier": "s",
}


def _text(name: str, value: str, *, pattern=False) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a bounded non-empty string")
    if len(value) > MAX_TEXT or (pattern and _ID.fullmatch(value) is None):
        raise ValueError(f"invalid {name}")
    return value


def _utc(name: str, raw: str) -> datetime:
    _text(name, raw)
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be ISO 8601 UTC") from error
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be ISO 8601 UTC")
    return value


@dataclass(frozen=True)
class HealthKitSourceRecord:
    external_id: str
    sample_type: str
    start_at: datetime | None
    end_at: datetime | None
    value: float | None
    unit: str | None
    source_name: str | None
    source_bundle_id: str | None
    device_model: str | None
    source_timezone: str | None
    workout_sport: str | None
    deleted: bool
    updated_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "HealthKitSourceRecord":
        if not isinstance(data, dict):
            raise ValueError("record must be an object")
        allowed = {
            "external_id", "sample_type", "start_at", "end_at", "value", "unit",
            "source_name", "source_bundle_id", "device_model", "source_timezone",
            "workout_sport", "deleted", "updated_at",
        }
        if not set(data) <= allowed:
            raise ValueError("record fields do not match contract")
        if not {"external_id", "sample_type", "deleted", "updated_at"} <= set(data):
            raise ValueError("record missing required identity fields")
        external_id = _text("external_id", data["external_id"], pattern=True)
        sample_type = _text("sample_type", data["sample_type"], pattern=True)
        if sample_type not in SUPPORTED_UNITS:
            raise ValueError("unsupported sample_type")
        deleted = data["deleted"]
        if not isinstance(deleted, bool):
            raise ValueError("deleted must be bool")
        updated_at = _utc("updated_at", data["updated_at"])
        if deleted:
            if any(data.get(name) is not None for name in ("start_at", "end_at", "value", "unit")):
                raise ValueError("deletion must not include sample value fields")
            start_at = end_at = value = unit = None
        else:
            if not {"start_at", "end_at", "value", "unit"} <= set(data):
                raise ValueError("active sample missing required value fields")
            start_at = _utc("start_at", data["start_at"])
            end_at = _utc("end_at", data["end_at"])
            if end_at < start_at:
                raise ValueError("end_at must not precede start_at")
            value = data["value"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError("value must be finite numeric")
            value = float(value)
            unit = _text("unit", data["unit"])
            if unit != SUPPORTED_UNITS[sample_type]:
                raise ValueError("unsupported unit for sample_type")
        metadata = []
        for name in ("source_name", "source_bundle_id", "device_model", "source_timezone"):
            raw = data.get(name)
            metadata.append(None if raw is None else _text(name, raw))
        workout_sport = data.get("workout_sport")
        if workout_sport is not None:
            workout_sport = _text("workout_sport", workout_sport)
        if sample_type != "HKWorkoutTypeIdentifier" and workout_sport is not None:
            raise ValueError("workout_sport is valid only for workouts")
        return cls(external_id, sample_type, start_at, end_at, value, unit, *metadata,
                   workout_sport, deleted, updated_at)


@dataclass(frozen=True)
class HealthKitBatch:
    batch_id: str
    device_id: str
    client_created_at: datetime
    records: tuple[HealthKitSourceRecord, ...]

    @classmethod
    def parse_partial(cls, data: dict) -> tuple["HealthKitBatch", tuple[str, ...]]:
        if not isinstance(data, dict) or set(data) != {
            "contract_version", "provider", "device_id", "batch_id", "records",
            "client_created_at",
        }:
            raise ValueError("batch fields do not match contract")
        if data["contract_version"] != HEALTHKIT_CONTRACT_VERSION:
            raise ValueError("unsupported contract_version")
        if data["provider"] != "healthkit":
            raise ValueError("provider must be healthkit")
        batch_id = _text("batch_id", data["batch_id"], pattern=True)
        device_id = _text("device_id", data["device_id"], pattern=True)
        created = _utc("client_created_at", data["client_created_at"])
        raw_records = data["records"]
        if not isinstance(raw_records, list) or not 1 <= len(raw_records) <= MAX_HEALTHKIT_BATCH_RECORDS:
            raise ValueError("records must contain 1..500 items")
        records = []
        rejected = []
        for index, row in enumerate(raw_records):
            try:
                records.append(HealthKitSourceRecord.from_dict(row))
            except (ValueError, TypeError):
                reference = row.get("external_id") if isinstance(row, dict) else None
                rejected.append(
                    reference if isinstance(reference, str) and _ID.fullmatch(reference)
                    else f"record:{index}"
                )
        return cls(batch_id, device_id, created, tuple(records)), tuple(rejected)

    @classmethod
    def from_dict(cls, data: dict) -> "HealthKitBatch":
        batch, rejected = cls.parse_partial(data)
        if rejected:
            raise ValueError("batch contains invalid records")
        return batch


@dataclass(frozen=True)
class HealthKitBatchAck:
    batch_id: str
    accepted: int
    duplicate: int
    rejected: int
    rejected_external_ids: tuple[str, ...]
    server_received_at: datetime

    @property
    def safe_to_advance_anchor(self) -> bool:
        return self.rejected == 0

    def to_dict(self) -> dict:
        return {
            "contract_version": HEALTHKIT_CONTRACT_VERSION,
            "batch_id": self.batch_id,
            "accepted": self.accepted,
            "duplicate": self.duplicate,
            "rejected": self.rejected,
            "rejected_external_ids": list(self.rejected_external_ids),
            "server_received_at": self.server_received_at.isoformat(),
            "safe_to_advance_anchor": self.safe_to_advance_anchor,
        }
