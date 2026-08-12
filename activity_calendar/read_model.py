"""Bounded calendar projection over persisted completed activities and training plans."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType
from training_plan.models import PlannedSession
from training_plan.repository import TrainingPlanRepository
from training_plan.selector import TrainingPlanSessionSelector


MAX_CALENDAR_RANGE_DAYS = 62


class ActivityCalendarProviderError(Exception):
    """Underlying persisted calendar source could not be read."""


class ActivityEventProvider(Protocol):
    def load_between(self, start: datetime, end: datetime) -> list[AthleteMemoryEvent]:
        ...


class PlannedSessionProvider(Protocol):
    def get_planned_sessions(
        self, target_date: date
    ) -> tuple[PlannedSession, ...]:
        ...


class RepositoryCalendarPlannedSessionProvider:
    """Calendar-specific adapter that preserves repository failure semantics."""

    def __init__(self, repository: TrainingPlanRepository) -> None:
        self._repository = repository
        self._selector = TrainingPlanSessionSelector()

    def get_planned_sessions(
        self, target_date: date
    ) -> tuple[PlannedSession, ...]:
        plan = self._repository.get_for_date(target_date)
        if plan is None:
            return ()
        return self._selector.get_all_for_date(plan, target_date)


@dataclass(frozen=True)
class CalendarActivity:
    activity_id: str
    sport: str | None
    start_time: datetime
    duration_seconds: float | None
    distance: float | None
    tss: float | None
    completed: bool | None
    status: str | None


@dataclass(frozen=True)
class CalendarDay:
    date: date
    planned_sessions: tuple[PlannedSession, ...]
    activities: tuple[CalendarActivity, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.planned_sessions, tuple):
            raise TypeError("planned_sessions must be tuple")

    @property
    def planned_session(self) -> PlannedSession | None:
        """Legacy singular projection; ambiguous multi-session dates return None."""
        return self.planned_sessions[0] if len(self.planned_sessions) == 1 else None


@dataclass(frozen=True)
class ActivityCalendar:
    start_date: date
    end_date: date
    timezone: str
    days: tuple[CalendarDay, ...]


def validate_calendar_range(start_date: date, end_date: date) -> None:
    if type(start_date) is not date or type(end_date) is not date:
        raise TypeError("start_date and end_date must be date instances")
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if (end_date - start_date).days + 1 > MAX_CALENDAR_RANGE_DAYS:
        raise ValueError(
            f"date range cannot exceed {MAX_CALENDAR_RANGE_DAYS} days"
        )


class ActivityCalendarBuilder:
    """Projects existing persisted facts without reanalysing activity data."""

    def __init__(
        self,
        activity_provider: ActivityEventProvider,
        planned_session_provider: PlannedSessionProvider,
        timezone_name: str = "Europe/Warsaw",
    ) -> None:
        try:
            self._timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"Unknown timezone '{timezone_name}'") from error
        self._timezone_name = timezone_name
        self._activity_provider = activity_provider
        self._planned_session_provider = planned_session_provider

    def build(self, start_date: date, end_date: date) -> ActivityCalendar:
        validate_calendar_range(start_date, end_date)
        exclusive_end_date = end_date + timedelta(days=1)

        # Athlete Memory records completion time. One-day margins keep the read
        # bounded while covering UTC/local-date offsets and activities crossing
        # midnight. Final inclusion uses persisted start time in athlete local time.
        query_start = datetime.combine(start_date - timedelta(days=1), time.min)
        query_end = datetime.combine(
            exclusive_end_date + timedelta(days=1), time.min
        )

        try:
            events = self._activity_provider.load_between(query_start, query_end)
            planned_by_date = {
                current_date: self._planned_session_provider.get_planned_sessions(
                    current_date
                )
                for current_date in _dates_inclusive(start_date, end_date)
            }
        except Exception as error:
            raise ActivityCalendarProviderError(
                "Activity Calendar source is temporarily unavailable"
            ) from error

        activities_by_date: dict[date, list[CalendarActivity]] = {
            current_date: []
            for current_date in _dates_inclusive(start_date, end_date)
        }
        try:
            for event in self._preferred_activity_events(events):
                activity = self._project_activity(event)
                local_date = self._local_datetime(activity.start_time).date()
                if local_date in activities_by_date:
                    activities_by_date[local_date].append(activity)
        except (KeyError, TypeError, ValueError) as error:
            raise ActivityCalendarProviderError(
                "Persisted activity data is invalid"
            ) from error

        days = tuple(
            CalendarDay(
                date=current_date,
                planned_sessions=planned_by_date[current_date],
                activities=tuple(
                    sorted(
                        activities_by_date[current_date],
                        key=lambda activity: (
                            self._local_datetime(activity.start_time),
                            activity.activity_id,
                        ),
                    )
                ),
            )
            for current_date in _dates_inclusive(start_date, end_date)
        )
        return ActivityCalendar(start_date, end_date, self._timezone_name, days)

    def _project_activity(self, event: AthleteMemoryEvent) -> CalendarActivity:
        if event.event_type not in (
            AthleteMemoryEventType.ACTIVITY_RECORDED,
            AthleteMemoryEventType.WORKOUT_COMPLETED,
        ):
            raise ValueError("Unsupported Athlete Memory event type")
        activity = event.payload["activity"]
        summary = event.payload.get("workout_summary", {})
        execution = event.payload.get("execution", {})
        feedback = event.payload.get("feedback", {})
        start_time = datetime.fromisoformat(activity["start"])

        return CalendarActivity(
            activity_id=event.event_id,
            sport=activity.get("sport"),
            start_time=start_time,
            duration_seconds=activity.get("duration"),
            distance=activity.get("distance"),
            tss=summary.get("tss"),
            completed=execution.get("completed"),
            status=feedback.get("status"),
        )

    @staticmethod
    def _preferred_activity_events(
        events: list[AthleteMemoryEvent],
    ) -> tuple[AthleteMemoryEvent, ...]:
        by_source: dict[tuple[str, str], AthleteMemoryEvent] = {}
        for event in events:
            if event.event_type not in (
                AthleteMemoryEventType.ACTIVITY_RECORDED,
                AthleteMemoryEventType.WORKOUT_COMPLETED,
            ):
                continue
            key = (event.source_type, event.source_key)
            current = by_source.get(key)
            if current is None or (
                event.event_type is AthleteMemoryEventType.ACTIVITY_RECORDED
                and current.event_type is AthleteMemoryEventType.WORKOUT_COMPLETED
            ):
                by_source[key] = event
        return tuple(by_source.values())

    def _local_datetime(self, value: datetime) -> datetime:
        # Existing FIT ingestion persists naive timestamps as athlete-local wall
        # time. Offset-aware timestamps are converted to the configured athlete zone.
        if value.tzinfo is None:
            return value.replace(tzinfo=self._timezone)
        return value.astimezone(self._timezone)


def _dates_inclusive(start_date: date, end_date: date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)
