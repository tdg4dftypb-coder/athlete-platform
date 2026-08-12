"""JSON serialization for the canonical Activity Calendar read model."""
from typing import Any

from activity_calendar.read_model import ActivityCalendar, CalendarActivity, CalendarDay
from training_plan.models import PlannedSession
from activity_reconciliation.serialization import ReconciliationResultSerializer


class ActivityCalendarSerializer:
    def __init__(self) -> None:
        self._reconciliation_serializer = ReconciliationResultSerializer()

    def serialize(self, calendar: ActivityCalendar) -> dict[str, Any]:
        return {
            "start_date": calendar.start_date.isoformat(),
            "end_date": calendar.end_date.isoformat(),
            "timezone": calendar.timezone,
            "days": [self._serialize_day(day) for day in calendar.days],
        }

    def _serialize_day(self, day: CalendarDay) -> dict[str, Any]:
        return {
            "date": day.date.isoformat(),
            "planned_sessions": [
                self._serialize_planned_session(session)
                for session in day.planned_sessions
            ],
            "planned_session": self._serialize_planned_session(day.planned_session),
            "activities": [
                self._serialize_activity(activity) for activity in day.activities
            ],
            "reconciliation": (
                None
                if day.reconciliation is None
                else self._reconciliation_serializer.serialize(day.reconciliation)
            ),
        }

    @staticmethod
    def _serialize_planned_session(
        session: PlannedSession | None,
    ) -> dict[str, Any] | None:
        if session is None:
            return None
        return {
            "session_id": session.session_id,
            "kind": session.kind.value,
            "session_type": session.session_type,
            "duration_minutes": session.duration_minutes,
            "target_tss": session.target_tss,
        }

    @staticmethod
    def _serialize_activity(activity: CalendarActivity) -> dict[str, Any]:
        return {
            "activity_id": activity.activity_id,
            "sport": activity.sport,
            "start_time": activity.start_time.isoformat(),
            "duration_seconds": activity.duration_seconds,
            "distance": activity.distance,
            "tss": activity.tss,
            "completed": activity.completed,
            "status": activity.status,
        }
