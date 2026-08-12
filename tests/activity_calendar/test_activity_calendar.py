from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from activity_calendar.read_model import (
    MAX_CALENDAR_RANGE_DAYS,
    ActivityCalendarBuilder,
    ActivityCalendarProviderError,
    RepositoryCalendarPlannedSessionProvider,
)
from activity_calendar.serialization import ActivityCalendarSerializer
from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from schema.athlete_memory_schema import AthleteMemorySchema
from server.app import create_dashboard_wsgi_app, create_production_dashboard_wsgi_app
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
from activity_reconciliation import (
    ActivityExecutionOutcome,
    ActivityReference,
    DuckDbReconciliationResultRepository,
    MatchStatus,
    ReconciliationItem,
    ReconciliationResult,
    ReplacementEvidence,
)


class EventProvider:
    def __init__(self, events=()):
        self.events = list(events)
        self.queries = []

    def load_between(self, start, end):
        self.queries.append((start, end))
        return [event for event in self.events if start <= event.occurred_at <= end]


class SessionProvider:
    def __init__(self, sessions=()):
        self.sessions = tuple(sessions)

    def get_planned_sessions(self, target_date):
        return tuple(sorted(
            (session for session in self.sessions if session.date == target_date),
            key=lambda session: (session.date, session.session_id),
        ))


def activity_event(
    event_id,
    start,
    *,
    event_type=AthleteMemoryEventType.WORKOUT_COMPLETED,
    duration=3600,
    distance=25000.0,
    tss=55.0,
    sport="cycling",
    completed=True,
    status="good",
):
    end = start + timedelta(seconds=duration or 0)
    event_end = end.replace(tzinfo=None) if end.tzinfo is not None else end
    return AthleteMemoryEvent(
        event_id=event_id,
        occurred_at=event_end,
        event_type=event_type,
        source_type="fit_file",
        source_key=f"source-{event_id}",
        schema_version=1,
        payload={
            "activity": {
                "start": start.isoformat(),
                "sport": sport,
                "duration": duration,
                "distance": distance,
            },
            "workout_summary": {"tss": tss},
            "execution": {"completed": completed},
            "feedback": {"status": status},
        },
    )


def planned_session(target_date):
    return PlannedSession(
        session_id=f"plan:{target_date.isoformat()}",
        date=target_date,
        kind=PlannedSessionKind.TRAINING,
        session_type="endurance",
        duration_minutes=60,
        target_tss=50.0,
        intensity="LOW",
        priority=3,
        rationale=("Baseline",),
    )


def builder(events=(), sessions=()):
    return ActivityCalendarBuilder(
        EventProvider(events),
        SessionProvider(sessions),
        timezone_name="Europe/Warsaw",
    )


def reconciliation_result(target, match_status, outcome=None):
    item = ReconciliationItem(
        match_status=match_status,
        planned_session_id="planned" if match_status is not MatchStatus.UNMATCHED_ACTIVITY else None,
        activity=(
            None if match_status is MatchStatus.UNMATCHED_PLANNED else
            ActivityReference("activity", "fit_file", "sha256:activity")
        ),
        candidate_session_ids=("planned",) if match_status is MatchStatus.AMBIGUOUS else (),
        candidate_activity_event_ids=("activity",) if match_status is MatchStatus.AMBIGUOUS else (),
        execution_outcome=outcome,
        completion_percent=50.0 if outcome is ActivityExecutionOutcome.PARTIAL else None,
        reason_codes=("evidence",),
        warning_codes=("warning",) if match_status is MatchStatus.AMBIGUOUS else (),
    )
    return ReconciliationResult(
        f"reconciliation:{match_status.value}", f"fingerprint:{match_status.value}",
        "1.0", target, "Europe/Warsaw", "plan", 2, True,
        ("planned",), ("activity",), (item,), (),
        datetime(2026, 8, 3, 5, tzinfo=timezone.utc),
    )


def test_valid_range_includes_every_ordered_day_and_uses_bounded_source_query():
    event_provider = EventProvider()
    calendar_builder = ActivityCalendarBuilder(event_provider, SessionProvider())

    calendar = calendar_builder.build(date(2026, 8, 1), date(2026, 8, 3))

    assert [day.date for day in calendar.days] == [
        date(2026, 8, 1),
        date(2026, 8, 2),
        date(2026, 8, 3),
    ]
    assert event_provider.queries == [
        (datetime(2026, 7, 31), datetime(2026, 8, 5))
    ]


def test_empty_range_has_empty_activity_lists_and_missing_plans_are_null():
    payload = ActivityCalendarSerializer().serialize(
        builder().build(date(2026, 8, 1), date(2026, 8, 2))
    )

    assert [day["activities"] for day in payload["days"]] == [[], []]
    assert [day["planned_sessions"] for day in payload["days"]] == [[], []]
    assert [day["planned_session"] for day in payload["days"]] == [None, None]
    assert [day["reconciliation"] for day in payload["days"]] == [None, None]


@pytest.mark.parametrize(
    ("match_status", "outcome"),
    [
        (MatchStatus.MATCHED, ActivityExecutionOutcome.COMPLETED),
        (MatchStatus.MATCHED, ActivityExecutionOutcome.PARTIAL),
        (MatchStatus.UNMATCHED_PLANNED, ActivityExecutionOutcome.SKIPPED),
        (MatchStatus.UNMATCHED_ACTIVITY, ActivityExecutionOutcome.UNPLANNED),
        (MatchStatus.AMBIGUOUS, None),
    ],
)
def test_http_calendar_serializes_persisted_reconciliation_outcomes(
    tmp_path, match_status, outcome
):
    target = date(2026, 8, 2)
    repository = DuckDbReconciliationResultRepository(tmp_path / "reconciliation.duckdb")
    persisted = reconciliation_result(target, match_status, outcome)
    repository.save(persisted)
    calendar_builder = ActivityCalendarBuilder(
        EventProvider(), SessionProvider(), reconciliation_provider=repository
    )
    response = call_app(
        create_dashboard_wsgi_app(activity_calendar_builder=calendar_builder),
        "start_date=2026-08-02&end_date=2026-08-02",
    )
    projection = response["payload"]["days"][0]["reconciliation"]
    item = projection["items"][0]
    assert response["status"] == "200 OK"
    assert projection["reconciliation_id"] == persisted.reconciliation_id
    assert projection["policy_version"] == "1.0"
    assert projection["target_local_date"] == "2026-08-02"
    assert projection["finalized"] is True
    assert projection["plan_id"] == "plan"
    assert projection["plan_version"] == 2
    assert projection["input_fingerprint"] == persisted.input_fingerprint
    assert item["match_status"] == match_status.value
    assert item["execution_outcome"] == (None if outcome is None else outcome.value)
    assert set(item) == {
        "match_status", "planned_session_id", "activity",
        "candidate_session_ids", "candidate_activity_event_ids",
        "execution_outcome", "completion_percent", "reason_codes",
        "warning_codes",
    }


def test_production_server_composition_reads_reconciliation_repository(tmp_path):
    target = date(2026, 8, 2)
    health_path = tmp_path / "health.duckdb"
    database = Database(health_path)
    AthleteMemorySchema(database).create()
    database.close()
    reconciliation_path = tmp_path / "reconciliation.duckdb"
    persisted = reconciliation_result(
        target, MatchStatus.MATCHED, ActivityExecutionOutcome.COMPLETED
    )
    DuckDbReconciliationResultRepository(reconciliation_path).save(persisted)
    app = create_production_dashboard_wsgi_app(
        health_db_path=health_path,
        biomarkers_db_path=tmp_path / "biomarkers.duckdb",
        decision_db_path=tmp_path / "decisions.duckdb",
        training_plan_db_path=tmp_path / "training_plan.duckdb",
        activity_reconciliation_db_path=reconciliation_path,
    )
    response = call_app(
        app, "start_date=2026-08-02&end_date=2026-08-02"
    )
    assert response["status"] == "200 OK"
    assert response["payload"]["days"][0]["reconciliation"][
        "reconciliation_id"
    ] == persisted.reconciliation_id


def test_reconciliation_serializer_preserves_replacement_evidence():
    target = date(2026, 8, 2)
    result = replace(
        reconciliation_result(
            target, MatchStatus.MATCHED, ActivityExecutionOutcome.REPLACED
        ),
        replacement_evidence=(ReplacementEvidence(
            planned_session_id="planned",
            activity_event_id="activity",
            source="athlete_confirmation",
            reason_code="manual_replacement",
            schema_version="2.0",
        ),),
    )
    class Provider:
        def get_latest_for_date(self, target_date):
            return result

    calendar = ActivityCalendarBuilder(
        EventProvider(), SessionProvider(), reconciliation_provider=Provider()
    ).build(target, target)
    payload = ActivityCalendarSerializer().serialize(calendar)
    assert payload["days"][0]["reconciliation"]["replacement_evidence"] == [{
        "planned_session_id": "planned",
        "activity_event_id": "activity",
        "source": "athlete_confirmation",
        "reason_code": "manual_replacement",
        "schema_version": "2.0",
    }]


def test_multiple_activities_are_grouped_by_day_and_ordered_by_start_then_id():
    events = [
        activity_event("later", datetime(2026, 8, 2, 18, 0)),
        activity_event("b", datetime(2026, 8, 2, 7, 0)),
        activity_event("a", datetime(2026, 8, 2, 7, 0)),
    ]

    calendar = builder(events).build(date(2026, 8, 2), date(2026, 8, 2))

    assert [activity.activity_id for activity in calendar.days[0].activities] == [
        "a",
        "b",
        "later",
    ]


def test_activities_are_grouped_across_multiple_days_with_stable_event_ids():
    events = [
        activity_event("stable-1", datetime(2026, 8, 1, 8, 0)),
        activity_event("stable-2", datetime(2026, 8, 3, 9, 0)),
    ]

    calendar = builder(events).build(date(2026, 8, 1), date(2026, 8, 3))

    assert [activity.activity_id for activity in calendar.days[0].activities] == [
        "stable-1"
    ]
    assert calendar.days[1].activities == ()
    assert [activity.activity_id for activity in calendar.days[2].activities] == [
        "stable-2"
    ]


def test_calendar_reads_activity_recorded_facts_without_feedback():
    event = activity_event(
        "fact-event",
        datetime(2026, 8, 2, 8, 0),
        event_type=AthleteMemoryEventType.ACTIVITY_RECORDED,
        status=None,
    )

    calendar = builder([event]).build(date(2026, 8, 2), date(2026, 8, 2))

    activity = calendar.days[0].activities[0]
    assert activity.activity_id == "fact-event"
    assert activity.status is None


@pytest.mark.parametrize("fact_first", [True, False])
def test_activity_recorded_precedes_workout_completed_for_same_source_identity(
    fact_first,
):
    workout_event = activity_event("workout", datetime(2026, 8, 2, 8, 0))
    fact_event = activity_event(
        "fact",
        datetime(2026, 8, 2, 8, 0),
        event_type=AthleteMemoryEventType.ACTIVITY_RECORDED,
    )
    fact_event = AthleteMemoryEvent(
        event_id=fact_event.event_id,
        occurred_at=fact_event.occurred_at,
        event_type=fact_event.event_type,
        source_type=workout_event.source_type,
        source_key=workout_event.source_key,
        schema_version=fact_event.schema_version,
        payload=fact_event.payload,
    )

    events = (
        [fact_event, workout_event]
        if fact_first
        else [workout_event, fact_event]
    )
    calendar = builder(events).build(date(2026, 8, 2), date(2026, 8, 2))

    assert [activity.activity_id for activity in calendar.days[0].activities] == [
        "fact"
    ]


def test_calendar_reads_the_production_athlete_memory_repository(tmp_path):
    database = Database(tmp_path / "memory.duckdb")
    AthleteMemorySchema(database).create()
    repository = AthleteMemoryRepository(database)
    repository.append(
        activity_event("persisted-event", datetime(2026, 8, 2, 8, 0))
    )

    calendar = ActivityCalendarBuilder(
        repository, SessionProvider()
    ).build(date(2026, 8, 2), date(2026, 8, 2))

    assert calendar.days[0].activities[0].activity_id == "persisted-event"
    database.close()


def test_planned_session_is_a_concise_existing_plan_projection():
    session = planned_session(date(2026, 8, 2))
    payload = ActivityCalendarSerializer().serialize(
        builder(sessions=[session]).build(date(2026, 8, 2), date(2026, 8, 2))
    )

    assert payload["days"][0]["planned_session"] == {
        "session_id": "plan:2026-08-02",
        "kind": "TRAINING",
        "session_type": "ENDURANCE",
        "duration_minutes": 60,
        "target_tss": 50.0,
    }
    assert payload["days"][0]["planned_sessions"] == [
        payload["days"][0]["planned_session"]
    ]


def test_calendar_day_carries_one_rest_session_as_an_immutable_tuple():
    target = date(2026, 8, 2)
    rest = PlannedSession(
        "plan:rest", target, PlannedSessionKind.REST, None, 0, 0.0, None, 1,
        ("Recovery",),
    )

    day = builder(sessions=(rest,)).build(target, target).days[0]

    assert day.planned_sessions == (rest,)
    assert day.planned_session == rest


def test_calendar_reads_the_production_training_plan_repository(tmp_path):
    target_date = date(2026, 8, 2)
    session = planned_session(target_date)
    repository = DuckDbTrainingPlanRepository(tmp_path / "plans.duckdb")
    repository.save(
        TrainingPlan(
            plan_id="calendar-plan",
            start_date=target_date,
            end_date=target_date,
            version=1,
            generated_at=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
            sessions=(session,),
        )
    )

    calendar = ActivityCalendarBuilder(
        EventProvider(), RepositoryCalendarPlannedSessionProvider(repository)
    ).build(target_date, target_date)

    assert calendar.days[0].planned_sessions == (session,)
    assert calendar.days[0].planned_session == session


def test_multi_session_calendar_and_serialization_preserve_canonical_order():
    target_date = date(2026, 8, 2)
    swim = PlannedSession(
        "plan:swim", target_date, PlannedSessionKind.TRAINING, "SWIM", 45,
        25.0, "EASY", 2, ("Technique",),
    )
    ride = PlannedSession(
        "plan:ride", target_date, PlannedSessionKind.TRAINING, "ENDURANCE", 180,
        130.0, "MODERATE", 4, ("Long ride",),
    )
    calendar = builder(sessions=(swim, ride)).build(target_date, target_date)
    payload = ActivityCalendarSerializer().serialize(calendar)

    assert calendar.days[0].planned_sessions == (ride, swim)
    assert calendar.days[0].planned_session is None
    assert [item["session_id"] for item in payload["days"][0]["planned_sessions"]] == [
        "plan:ride",
        "plan:swim",
    ]
    assert payload["days"][0]["planned_session"] is None


def test_missing_optional_activity_fields_serialize_as_null_without_fabrication():
    event = activity_event(
        "partial",
        datetime(2026, 8, 2, 8, 0),
        duration=None,
        distance=None,
        tss=None,
        sport=None,
        completed=None,
        status=None,
    )

    payload = ActivityCalendarSerializer().serialize(
        builder([event]).build(date(2026, 8, 2), date(2026, 8, 2))
    )
    activity = payload["days"][0]["activities"][0]

    assert activity == {
        "activity_id": "partial",
        "sport": None,
        "start_time": "2026-08-02T08:00:00",
        "duration_seconds": None,
        "distance": None,
        "tss": None,
        "completed": None,
        "status": None,
    }


def test_offset_aware_start_is_assigned_to_athlete_local_day():
    # 22:30 UTC is 00:30 on the following day in Warsaw in August.
    event = activity_event(
        "near-midnight",
        datetime(2026, 8, 1, 22, 30, tzinfo=timezone.utc),
    )

    calendar = builder([event]).build(date(2026, 8, 2), date(2026, 8, 2))

    assert calendar.days[0].activities[0].activity_id == "near-midnight"


def test_naive_persisted_start_uses_existing_athlete_local_wall_time_semantics():
    event = activity_event("local", datetime(2026, 8, 2, 0, 15))

    calendar = builder([event]).build(date(2026, 8, 2), date(2026, 8, 2))

    assert calendar.days[0].activities[0].activity_id == "local"


@pytest.mark.parametrize(
    "start_date,end_date",
    [
        (date(2026, 8, 2), date(2026, 8, 1)),
        (
            date(2026, 1, 1),
            date(2026, 1, 1) + timedelta(days=MAX_CALENDAR_RANGE_DAYS),
        ),
    ],
)
def test_invalid_or_over_maximum_range_is_rejected(start_date, end_date):
    with pytest.raises(ValueError):
        builder().build(start_date, end_date)


def test_provider_failure_has_a_specific_read_model_error():
    class FailingProvider:
        def load_between(self, start, end):
            raise RuntimeError("database unavailable")

    calendar_builder = ActivityCalendarBuilder(FailingProvider(), SessionProvider())

    with pytest.raises(ActivityCalendarProviderError):
        calendar_builder.build(date(2026, 8, 1), date(2026, 8, 1))


def test_planning_provider_failure_has_a_specific_read_model_error():
    class FailingSessionProvider:
        def get_planned_sessions(self, target_date):
            raise RuntimeError("training plan database unavailable")

    calendar_builder = ActivityCalendarBuilder(
        EventProvider(), FailingSessionProvider()
    )

    with pytest.raises(ActivityCalendarProviderError):
        calendar_builder.build(date(2026, 8, 1), date(2026, 8, 1))


def call_app(app, query_string):
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = headers

    body = app(
        {
            "PATH_INFO": "/api/v1/activity-calendar",
            "REQUEST_METHOD": "GET",
            "QUERY_STRING": query_string,
        },
        start_response,
    )
    response["payload"] = json.loads(body[0])
    return response


def test_http_contract_returns_bounded_calendar_payload():
    event = activity_event("event-1", datetime(2026, 8, 2, 8, 0))
    app = create_dashboard_wsgi_app(
        activity_calendar_builder=builder([event])
    )

    response = call_app(app, "start_date=2026-08-01&end_date=2026-08-03")

    assert response["status"] == "200 OK"
    assert set(response["payload"]) == {
        "start_date",
        "end_date",
        "timezone",
        "days",
    }
    assert response["payload"]["timezone"] == "Europe/Warsaw"
    assert len(response["payload"]["days"]) == 3


def test_http_contract_returns_multi_session_day_without_ambiguity():
    target = date(2026, 8, 2)
    swim = PlannedSession(
        "plan:swim", target, PlannedSessionKind.TRAINING, "SWIM", 45,
        25.0, "EASY", 2, (),
    )
    ride = PlannedSession(
        "plan:ride", target, PlannedSessionKind.TRAINING, "ENDURANCE", 180,
        130.0, "MODERATE", 4, (),
    )
    app = create_dashboard_wsgi_app(
        activity_calendar_builder=builder(sessions=(swim, ride))
    )

    response = call_app(app, "start_date=2026-08-02&end_date=2026-08-02")

    assert response["status"] == "200 OK"
    day = response["payload"]["days"][0]
    assert [item["session_id"] for item in day["planned_sessions"]] == [
        "plan:ride",
        "plan:swim",
    ]
    assert day["planned_session"] is None


@pytest.mark.parametrize(
    "query_string",
    [
        "",
        "start_date=2026-08-01",
        "start_date=not-a-date&end_date=2026-08-02",
        "start_date=2026-08-03&end_date=2026-08-02",
        "start_date=2026-01-01&end_date=2026-03-04",
    ],
)
def test_http_contract_rejects_invalid_queries(query_string):
    response = call_app(create_dashboard_wsgi_app(), query_string)

    assert response["status"] == "400 Bad Request"
    assert "error" in response["payload"]


def test_http_contract_maps_provider_failure_to_503_without_leaking_details():
    class FailingBuilder:
        def build(self, start_date, end_date):
            raise ActivityCalendarProviderError("secret database path")

    app = create_dashboard_wsgi_app(activity_calendar_builder=FailingBuilder())
    response = call_app(app, "start_date=2026-08-01&end_date=2026-08-02")

    assert response["status"] == "503 Service Unavailable"
    assert "secret" not in response["payload"]["error"]
