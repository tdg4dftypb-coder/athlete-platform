"""Immutable evidence snapshot models for future adaptation policy input."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from math import isfinite

from activity_reconciliation.models import MatchStatus, ReconciliationResult
from application.athlete_assessment import AthleteAssessment
from training_plan.intent import Weekday
from training_plan.models import PlannedSession, PlannedSessionKind

from plan_adaptation.models import (
    AdaptationContextWindow,
    AdaptationWarningCode,
    AdaptationWindow,
    _require_date,
    _require_non_empty,
    _validate_codes,
    _validate_fingerprint,
)


class AdaptationConstraintType(Enum):
    FIXED_SESSION = "fixed_session"
    PROTECTED_RECOVERY_DAY = "protected_recovery_day"
    AVAILABILITY = "availability"


@dataclass(frozen=True)
class AdaptationConstraint:
    constraint_id: str
    constraint_type: AdaptationConstraintType
    weekday: Weekday | None = None
    session_id: str | None = None
    session_type: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("constraint_id", self.constraint_id)
        if not isinstance(self.constraint_type, AdaptationConstraintType):
            raise TypeError("constraint_type must be AdaptationConstraintType")
        if self.weekday is not None and not isinstance(self.weekday, Weekday):
            raise TypeError("weekday must be Weekday when provided")
        for name in ("session_id", "session_type"):
            value = getattr(self, name)
            if value is not None:
                _require_non_empty(name, value)
        if self.session_type is not None:
            object.__setattr__(self, "session_type", self.session_type.strip().upper())
        if self.weekday is None and self.session_id is None and self.session_type is None:
            raise ValueError("constraint must identify a weekday, session_id, or session_type")


@dataclass(frozen=True)
class WeeklyRhythmSlot:
    kind: PlannedSessionKind
    session_type: str | None
    fixed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PlannedSessionKind):
            raise TypeError("kind must be PlannedSessionKind")
        if not isinstance(self.fixed, bool):
            raise TypeError("fixed must be bool")
        if self.kind is PlannedSessionKind.TRAINING:
            _require_non_empty("session_type", self.session_type)
            object.__setattr__(self, "session_type", self.session_type.strip().upper())
        elif self.session_type is not None:
            raise ValueError("REST rhythm slot session_type must be None")


@dataclass(frozen=True)
class WeeklyRhythmDay:
    weekday: Weekday
    slots: tuple[WeeklyRhythmSlot, ...]
    protected_recovery: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.weekday, Weekday):
            raise TypeError("weekday must be Weekday")
        if not isinstance(self.slots, tuple):
            raise TypeError("slots must be tuple")
        if any(not isinstance(slot, WeeklyRhythmSlot) for slot in self.slots):
            raise TypeError("slots must contain only WeeklyRhythmSlot")
        if not isinstance(self.protected_recovery, bool):
            raise TypeError("protected_recovery must be bool")
        canonical = tuple(sorted(self.slots, key=lambda slot: (slot.kind.value, slot.session_type or "", slot.fixed)))
        object.__setattr__(self, "slots", canonical)


@dataclass(frozen=True)
class WeeklyRhythm:
    rhythm_id: str
    days: tuple[WeeklyRhythmDay, ...]

    def __post_init__(self) -> None:
        _require_non_empty("rhythm_id", self.rhythm_id)
        if not isinstance(self.days, tuple):
            raise TypeError("days must be tuple")
        if len(self.days) != 7 or any(not isinstance(day, WeeklyRhythmDay) for day in self.days):
            raise ValueError("weekly rhythm must contain exactly seven WeeklyRhythmDay values")
        if len({day.weekday for day in self.days}) != 7:
            raise ValueError("weekly rhythm must contain every weekday exactly once")
        object.__setattr__(self, "days", tuple(sorted(self.days, key=lambda day: day.weekday.value)))


@dataclass(frozen=True)
class AdaptationTrainingLoad:
    recent_training_load_7d: float | None = None
    ctl: float | None = None
    atl: float | None = None
    tsb: float | None = None

    def __post_init__(self) -> None:
        for name in ("recent_training_load_7d", "ctl", "atl", "tsb"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                raise TypeError(f"{name} must be numeric when provided")
            if value is not None and not isfinite(value):
                raise ValueError(f"{name} must be finite when provided")
            if value is not None:
                object.__setattr__(self, name, float(value))
        if self.recent_training_load_7d is not None and self.recent_training_load_7d < 0:
            raise ValueError("recent_training_load_7d must be >= 0")
        if self.ctl is not None and self.ctl < 0:
            raise ValueError("ctl must be >= 0")
        if self.atl is not None and self.atl < 0:
            raise ValueError("atl must be >= 0")

    @property
    def available_metric_count(self) -> int:
        return sum(value is not None for value in (self.recent_training_load_7d, self.ctl, self.atl, self.tsb))


@dataclass(frozen=True)
class AdaptationHistoryDay:
    day: date
    planned_sessions: tuple[PlannedSession, ...]
    reconciliation: ReconciliationResult | None

    def __post_init__(self) -> None:
        _require_date("day", self.day)
        if not isinstance(self.planned_sessions, tuple):
            raise TypeError("planned_sessions must be tuple")
        if any(not isinstance(session, PlannedSession) for session in self.planned_sessions):
            raise TypeError("planned_sessions must contain only PlannedSession")
        if any(session.date != self.day for session in self.planned_sessions):
            raise ValueError("historical planned session date must match day")
        if len({session.session_id for session in self.planned_sessions}) != len(self.planned_sessions):
            raise ValueError("historical day contains duplicate session_id")
        object.__setattr__(self, "planned_sessions", tuple(sorted(self.planned_sessions, key=lambda session: session.session_id)))
        if self.reconciliation is not None:
            if not isinstance(self.reconciliation, ReconciliationResult):
                raise TypeError("reconciliation must be ReconciliationResult when provided")
            if self.reconciliation.target_local_date != self.day:
                raise ValueError("reconciliation target_local_date must match day")

    @property
    def is_ambiguous(self) -> bool:
        return self.reconciliation is not None and any(
            item.match_status is MatchStatus.AMBIGUOUS for item in self.reconciliation.items
        )


@dataclass(frozen=True)
class AdaptationContext:
    evaluation_date: date
    context_window: AdaptationContextWindow
    mutation_window: AdaptationWindow
    source_plan_id: str
    source_plan_version: int
    historical_days: tuple[AdaptationHistoryDay, ...]
    future_sessions: tuple[PlannedSession, ...]
    training_load: AdaptationTrainingLoad | None
    athlete_state: AthleteAssessment | None
    constraints: tuple[AdaptationConstraint, ...]
    weekly_rhythm: WeeklyRhythm | None
    warning_codes: tuple[AdaptationWarningCode, ...]
    input_fingerprint: str
    built_at: datetime

    def __post_init__(self) -> None:
        _require_date("evaluation_date", self.evaluation_date)
        if self.context_window != AdaptationContextWindow.canonical(self.evaluation_date):
            raise ValueError("context_window must be canonical for evaluation_date")
        if self.mutation_window != AdaptationWindow.canonical(self.evaluation_date):
            raise ValueError("mutation_window must be canonical for evaluation_date")
        _require_non_empty("source_plan_id", self.source_plan_id)
        if not isinstance(self.source_plan_version, int) or isinstance(self.source_plan_version, bool) or self.source_plan_version < 1:
            raise ValueError("source_plan_version must be int >= 1")
        if not isinstance(self.historical_days, tuple) or len(self.historical_days) != 8:
            raise ValueError("historical_days must contain exactly D-7 through D")
        if any(not isinstance(item, AdaptationHistoryDay) for item in self.historical_days):
            raise TypeError("historical_days must contain only AdaptationHistoryDay")
        expected_days = tuple(
            self.context_window.context_start + timedelta(days=offset)
            for offset in range(8)
        )
        if tuple(item.day for item in self.historical_days) != expected_days:
            raise ValueError("historical_days must be canonically ordered D-7 through D")
        if not isinstance(self.future_sessions, tuple):
            raise TypeError("future_sessions must be tuple")
        if any(not isinstance(session, PlannedSession) for session in self.future_sessions):
            raise TypeError("future_sessions must contain only PlannedSession")
        if len({session.session_id for session in self.future_sessions}) != len(self.future_sessions):
            raise ValueError("future_sessions contains duplicate session_id")
        if any(not (self.mutation_window.mutation_start <= session.date <= self.mutation_window.mutation_end) for session in self.future_sessions):
            raise ValueError("future session lies outside mutation window")
        if tuple(sorted(self.future_sessions, key=lambda session: (session.date, session.session_id))) != self.future_sessions:
            raise ValueError("future_sessions must be canonically ordered")
        if self.training_load is not None and not isinstance(self.training_load, AdaptationTrainingLoad):
            raise TypeError("training_load must be AdaptationTrainingLoad when provided")
        if self.athlete_state is not None and not isinstance(self.athlete_state, AthleteAssessment):
            raise TypeError("athlete_state must be AthleteAssessment when provided")
        if not isinstance(self.constraints, tuple) or any(not isinstance(item, AdaptationConstraint) for item in self.constraints):
            raise TypeError("constraints must be a tuple of AdaptationConstraint")
        if len({item.constraint_id for item in self.constraints}) != len(self.constraints):
            raise ValueError("constraints contains duplicate constraint_id")
        if tuple(sorted(self.constraints, key=lambda item: item.constraint_id)) != self.constraints:
            raise ValueError("constraints must be canonically ordered")
        if self.weekly_rhythm is not None and not isinstance(self.weekly_rhythm, WeeklyRhythm):
            raise TypeError("weekly_rhythm must be WeeklyRhythm when provided")
        canonical_warnings = _validate_codes("warning_codes", self.warning_codes, AdaptationWarningCode)
        object.__setattr__(self, "warning_codes", canonical_warnings)
        _validate_fingerprint(self.input_fingerprint)
        if not isinstance(self.built_at, datetime):
            raise TypeError("built_at must be datetime")
