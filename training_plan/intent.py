"""Intent models for weekly baseline training plan templates."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from training_plan.models import PlannedSessionKind


class Weekday(IntEnum):
    """Python-compatible weekday numbering matching date.weekday().

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
    """
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass(frozen=True)
class WeeklySessionIntent:
    """Immutable template for a recurring weekly session intent on a specific Weekday."""

    weekday: Weekday
    kind: PlannedSessionKind
    session_type: str | None
    duration_minutes: int
    target_tss: float | None
    intensity: str | None
    priority: int
    rationale: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.weekday, Weekday):
            raise TypeError("weekday must be Weekday instance")

        if not isinstance(self.kind, PlannedSessionKind):
            raise TypeError("kind must be PlannedSessionKind")

        if not isinstance(self.duration_minutes, int):
            raise TypeError("duration_minutes must be int")
        if self.duration_minutes < 0:
            raise ValueError("duration_minutes cannot be negative")

        if self.target_tss is not None:
            if not isinstance(self.target_tss, (int, float)):
                raise TypeError("target_tss must be float or int")
            if self.target_tss < 0.0:
                raise ValueError("target_tss cannot be negative")

        if not isinstance(self.priority, int):
            raise TypeError("priority must be int")
        if not (1 <= self.priority <= 5):
            raise ValueError("priority must be bounded between 1 and 5")

        if not isinstance(self.rationale, tuple):
            raise TypeError("rationale must be tuple")
        for item in self.rationale:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("rationale items must be non-empty strings")

        if self.kind == PlannedSessionKind.TRAINING:
            if not isinstance(self.session_type, str) or not self.session_type.strip():
                raise ValueError("TRAINING session_type must be non-empty string")
            object.__setattr__(self, "session_type", self.session_type.strip().upper())

            if self.duration_minutes <= 0:
                raise ValueError("TRAINING duration_minutes must be > 0")

            if self.intensity is not None:
                if not isinstance(self.intensity, str) or not self.intensity.strip():
                    raise ValueError("intensity must be non-empty string if provided")
                object.__setattr__(self, "intensity", self.intensity.strip().upper())

        elif self.kind == PlannedSessionKind.REST:
            if self.session_type is not None:
                raise ValueError("REST session_type must be None")

            if self.duration_minutes != 0:
                raise ValueError("REST duration_minutes must be 0")

            if self.target_tss is not None and self.target_tss != 0.0:
                raise ValueError("REST target_tss must be None or 0.0")
            object.__setattr__(self, "target_tss", 0.0)

            if self.intensity is not None:
                raise ValueError("REST intensity must be None")


@dataclass(frozen=True)
class TrainingIntent:
    """Immutable recurring 7-day weekly training intent configuration.

    Guarantees exactly one WeeklySessionIntent for every Weekday (Monday through Sunday).
    Stores sessions canonically ordered from Monday (0) to Sunday (6).
    """

    intent_id: str
    weekly_sessions: tuple[WeeklySessionIntent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.intent_id, str) or not self.intent_id.strip():
            raise ValueError("intent_id must be non-empty string")

        if not isinstance(self.weekly_sessions, tuple):
            raise TypeError("weekly_sessions must be tuple")

        if len(self.weekly_sessions) != 7:
            raise ValueError(f"TrainingIntent requires exactly 7 weekly sessions, got {len(self.weekly_sessions)}")

        seen_weekdays = set()
        for idx, item in enumerate(self.weekly_sessions):
            if not isinstance(item, WeeklySessionIntent):
                raise TypeError(f"item at index {idx} must be WeeklySessionIntent")
            if item.weekday in seen_weekdays:
                raise ValueError(f"duplicate weekday '{item.weekday.name}' in TrainingIntent")
            seen_weekdays.add(item.weekday)

        if len(seen_weekdays) != 7:
            raise ValueError("TrainingIntent must contain exactly one entry for each of the 7 weekdays")

        # Canonicalize order Monday -> Sunday
        sorted_sessions = tuple(sorted(self.weekly_sessions, key=lambda s: s.weekday.value))
        object.__setattr__(self, "weekly_sessions", sorted_sessions)
