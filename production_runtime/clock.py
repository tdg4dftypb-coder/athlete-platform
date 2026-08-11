"""Explicit UTC clock and athlete-local target-date boundary."""
from datetime import date, datetime, timezone
from typing import Protocol, runtime_checkable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@runtime_checkable
class RuntimeClock(Protocol):
    def now_utc(self) -> datetime:
        ...


class SystemUtcRuntimeClock:
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


def target_local_date_at(instant_utc: datetime, timezone_name: str = "Europe/Warsaw") -> date:
    """Derive one target date at the runtime boundary, never inside phases."""
    if not isinstance(instant_utc, datetime):
        raise TypeError("instant_utc must be a datetime")
    if instant_utc.tzinfo is None or instant_utc.utcoffset() is None:
        raise ValueError("instant_utc must be timezone-aware")
    if instant_utc.utcoffset() != timezone.utc.utcoffset(instant_utc):
        raise ValueError("instant_utc must use UTC")
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        raise ValueError("timezone_name must be a non-empty string")
    try:
        athlete_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Unknown timezone '{timezone_name}'") from error
    return instant_utc.astimezone(athlete_timezone).date()
