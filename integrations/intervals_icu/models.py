"""Versioned normalized Intervals.icu source contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite
import os

from .errors import ConfigurationMissing, MalformedResponse

CONTRACT_VERSION = "1.0"
PROVIDER = "intervals_icu"


def utc(raw, name: str) -> datetime:
    if not isinstance(raw, str):
        raise MalformedResponse(f"{name} is required")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise MalformedResponse(f"invalid {name}") from error
    if value.tzinfo is None:
        raise MalformedResponse(f"{name} must include timezone")
    return value.astimezone(timezone.utc)


def number(data: dict, *names: str, minimum=0.0, maximum=10_000_000.0):
    raw = next((data[name] for name in names if data.get(name) is not None), None)
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not isfinite(raw):
        raise MalformedResponse(f"invalid {names[0]}")
    value = float(raw)
    if not minimum <= value <= maximum:
        raise MalformedResponse(f"invalid {names[0]}")
    return value


class Sport(str, Enum):
    RIDE = "RIDE"
    RUN = "RUN"
    SWIM = "SWIM"
    WALK = "WALK"
    HIKE = "HIKE"
    WEIGHT_TRAINING = "WEIGHT_TRAINING"
    OTHER = "OTHER"

    @classmethod
    def from_provider(cls, value) -> "Sport":
        normalized = str(value or "").replace("_", "").replace(" ", "").lower()
        return {
            "ride": cls.RIDE, "virtualride": cls.RIDE, "ebikeride": cls.RIDE,
            "run": cls.RUN, "virtualrun": cls.RUN, "trailrun": cls.RUN,
            "swim": cls.SWIM, "walk": cls.WALK, "hike": cls.HIKE,
            "weighttraining": cls.WEIGHT_TRAINING,
        }.get(normalized, cls.OTHER)


@dataclass(frozen=True)
class IntervalsConfiguration:
    athlete_id: str | None
    api_key: str | None

    @classmethod
    def from_environment(cls, environ=None):
        source = os.environ if environ is None else environ
        return cls(source.get("INTERVALS_ATHLETE_ID"), source.get("INTERVALS_API_KEY"))

    @property
    def enabled(self) -> bool:
        return bool(self.athlete_id and self.api_key)

    def require(self) -> "IntervalsConfiguration":
        if not self.enabled:
            raise ConfigurationMissing("Intervals.icu provider is disabled")
        if any(char in self.athlete_id for char in "/?#"):
            raise ConfigurationMissing("invalid athlete id")
        return self


@dataclass(frozen=True)
class IntervalsActivity:
    external_id: str
    updated_at: datetime
    start_at: datetime
    end_at: datetime
    sport: Sport
    duration_seconds: float
    distance_meters: float | None
    intervals_external_tss: float | None
    intervals_external_intensity: float | None
    average_heart_rate: float | None
    average_power: float | None
    weighted_average_power: float | None
    average_cadence: float | None
    archived: bool

    @classmethod
    def from_provider(cls, data: dict) -> "IntervalsActivity":
        if not isinstance(data, dict):
            raise MalformedResponse("activity must be an object")
        external_id = data.get("id")
        if not isinstance(external_id, (str, int)) or not str(external_id).strip():
            raise MalformedResponse("activity id is required")
        start = utc(data.get("start_date"), "start_date")
        duration = number(data, "elapsed_time", "moving_time", maximum=604_800)
        if duration is None:
            raise MalformedResponse("elapsed_time or moving_time is required")
        updated_raw = data.get("updated") or data.get("icu_sync_date") or data.get("analyzed") or data.get("created")
        updated = utc(updated_raw, "provider updated timestamp")
        return cls(
            str(external_id), updated, start,
            start + timedelta(seconds=duration),
            Sport.from_provider(data.get("type")), duration,
            number(data, "distance", maximum=10_000_000),
            number(data, "icu_training_load", maximum=10_000),
            number(data, "icu_intensity", maximum=1_000),
            number(data, "average_heartrate", "average_hr", maximum=300),
            number(data, "average_watts", maximum=5_000),
            number(data, "weighted_average_watts", maximum=5_000),
            number(data, "average_cadence", maximum=500),
            bool(data.get("deleted", False) or data.get("archived", False)),
        )


@dataclass(frozen=True)
class IntervalsSyncResult:
    fetched: int
    inserted: int
    updated: int
    unchanged: int
    archived: int
    rejected: int
    watermark_before: datetime | None
    watermark_after: datetime | None
    started_at: datetime
    completed_at: datetime
    provider_status: str
