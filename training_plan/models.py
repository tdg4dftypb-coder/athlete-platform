"""Domain models and enums for Training Plan Bounded Context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class PlannedSessionKind(Enum):
    """Discriminates intentional training sessions from intentional rest days."""
    TRAINING = "TRAINING"
    REST = "REST"


@dataclass(frozen=True)
class PlannedSession:
    """Immutable representation of a single day's planned training intent or rest.

    Priority range is defined as 1 (lowest) to 5 (highest).
    Canonical representation of Target TSS for REST days is 0.0.
    Casing for session_type is normalized to UPPERCASE (whitespace trimmed).
    """

    session_id: str
    date: date
    kind: PlannedSessionKind
    session_type: str | None
    duration_minutes: int
    target_tss: float | None
    intensity: str | None
    priority: int
    rationale: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("session_id must be non-empty string")

        if type(self.date) is not date:
            raise TypeError("date must be a date instance (not datetime)")

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
class TrainingPlan:
    """Immutable multi-day baseline training calendar.

    Guarantees intentional coverage for every date in [start_date, end_date].
    A date contains exactly one REST session or one-or-more TRAINING sessions.
    Sessions are canonically ordered by (date, session_id).
    """

    plan_id: str
    start_date: date
    end_date: date
    version: int
    generated_at: datetime
    sessions: tuple[PlannedSession, ...]
    supersedes_plan_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("plan_id must be non-empty string")

        if type(self.start_date) is not date:
            raise TypeError("start_date must be date instance")
        if type(self.end_date) is not date:
            raise TypeError("end_date must be date instance")
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")

        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be int >= 1")

        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be datetime instance")

        if not isinstance(self.sessions, tuple):
            raise TypeError("sessions must be tuple")

        if self.supersedes_plan_id is not None:
            if not isinstance(self.supersedes_plan_id, str) or not self.supersedes_plan_id.strip():
                raise ValueError("supersedes_plan_id must be non-empty string if specified")
            if self.supersedes_plan_id == self.plan_id:
                raise ValueError("plan cannot supersede itself")

        for idx, session in enumerate(self.sessions):
            if not isinstance(session, PlannedSession):
                raise TypeError(f"item at index {idx} must be PlannedSession")

        # Normalize independently constructed/decoded plans to canonical order.
        canonical_sessions = tuple(sorted(self.sessions, key=lambda s: (s.date, s.session_id)))
        object.__setattr__(self, "sessions", canonical_sessions)

        # Validate unique session IDs, valid dates, and per-date semantics.
        seen_session_ids = set()
        sessions_by_date: dict[date, list[PlannedSession]] = {}

        for idx, s in enumerate(self.sessions):
            if s.session_id in seen_session_ids:
                raise ValueError(f"duplicate session_id '{s.session_id}' found in plan")
            seen_session_ids.add(s.session_id)

            if s.date < self.start_date or s.date > self.end_date:
                raise ValueError(f"session date {s.date} lies outside plan range [{self.start_date}, {self.end_date}]")

            sessions_by_date.setdefault(s.date, []).append(s)

        for session_date, day_sessions in sessions_by_date.items():
            rest_count = sum(s.kind is PlannedSessionKind.REST for s in day_sessions)
            if rest_count and len(day_sessions) != 1:
                raise ValueError(
                    f"date {session_date} must contain exactly one REST session "
                    "or one-or-more TRAINING sessions"
                )

        # Validate complete intentional calendar coverage.
        total_days = (self.end_date - self.start_date).days + 1
        if len(sessions_by_date) != total_days:
            raise ValueError(
                f"plan range [{self.start_date}, {self.end_date}] requires intentional "
                f"coverage for exactly {total_days} dates, but got {len(sessions_by_date)}"
            )
