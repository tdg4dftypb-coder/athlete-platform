from datetime import date, datetime, timedelta, timezone

import pytest

from activity_reconciliation import (
    ActivityExecutionOutcome,
    ActivitySessionReconciler,
    DuckDbReconciliationResultRepository,
    MatchStatus,
)
from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType
from production_runtime.coordinator import RuntimePhaseContext
from production_runtime.models import (
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimePhase,
    RuntimeStatus,
    logical_execution_key,
)
from production_runtime.reconciliation import (
    ProductionReconciliationAdapter,
    RECONCILIATION_PLAN_UNAVAILABLE,
)
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan


TARGET = date(2026, 8, 12)
CLOSED = TARGET - timedelta(days=1)
NOW = datetime(2026, 8, 12, 5, tzinfo=timezone.utc)


class Clock:
    def now_utc(self):
        return NOW


class Plans:
    def __init__(self, value):
        self.value = value
        self.requested = []
    def get_for_date(self, target_date):
        self.requested.append(target_date)
        return self.value


class Memory:
    def __init__(self, events=()):
        self.events = list(events)
        self.queries = []
    def load_between(self, start, end):
        self.queries.append((start, end))
        return [event for event in self.events if start <= event.occurred_at <= end]


def session(session_id="ride", session_type="ENDURANCE", minutes=60):
    return PlannedSession(
        session_id, CLOSED, PlannedSessionKind.TRAINING, session_type, minutes,
        50.0, "LOW", 2, (),
    )


def plan(*sessions, version=1):
    return TrainingPlan("plan", CLOSED, CLOSED, version, NOW, tuple(sessions))


def rest():
    return PlannedSession(
        "rest", CLOSED, PlannedSessionKind.REST, None, 0, 0.0, None, 1, (),
    )


def event(event_id="activity", sport="cycling", duration=3600, start=None,
          event_type=AthleteMemoryEventType.ACTIVITY_RECORDED):
    start = start or datetime(2026, 8, 11, 10)
    return AthleteMemoryEvent(
        event_id, start + timedelta(seconds=duration), event_type,
        "fit_file", f"sha256:{event_id}", 1,
        {"activity": {
            "start": start.isoformat(), "sport": sport, "duration": duration,
        }},
    )


def context():
    return RuntimePhaseContext(ProductionDailyRuntimeResult(
        runtime_id="runtime", logical_execution_key=logical_execution_key(TARGET),
        revision=1, contract_version="1.0", target_local_date=TARGET,
        timezone_name="Europe/Warsaw", started_at_utc=NOW,
        completed_at_utc=None, status=RuntimeStatus.RUNNING,
    ))


def adapter(tmp_path, training_plan, events=()):
    plans = Plans(training_plan)
    memory = Memory(events)
    repository = DuckDbReconciliationResultRepository(tmp_path / "reconciliation.duckdb")
    value = ProductionReconciliationAdapter(
        plans, memory, repository, ActivitySessionReconciler(), Clock(),
        "Europe/Warsaw",
    )
    return value, plans, memory, repository


def test_adapter_reconciles_previous_closed_date_and_reports_exact_evidence(tmp_path):
    value, plans, memory, repository = adapter(
        tmp_path, plan(session()), [event()]
    )

    outcome = value.execute(context())
    persisted = repository.get_by_id(outcome.artifact_ids[0])

    assert plans.requested == [CLOSED]
    assert memory.queries == [
        (datetime(2026, 8, 10), datetime(2026, 8, 13))
    ]
    assert outcome.status is PhaseStatus.COMPLETED
    assert outcome.changed_state is True
    assert outcome.item_count == 1
    assert outcome.reconciliations_created == 1
    assert persisted.target_local_date == CLOSED
    assert persisted.finalized is True
    assert persisted.items[0].execution_outcome is ActivityExecutionOutcome.COMPLETED


@pytest.mark.parametrize(
    ("sessions", "events", "statuses", "outcomes"),
    [
        ((session(),), (event(duration=1800),), {MatchStatus.MATCHED},
         {ActivityExecutionOutcome.PARTIAL}),
        ((session(),), (), {MatchStatus.UNMATCHED_PLANNED},
         {ActivityExecutionOutcome.SKIPPED}),
        ((rest(),), (event(),),
         {MatchStatus.UNMATCHED_PLANNED, MatchStatus.UNMATCHED_ACTIVITY},
         {None, ActivityExecutionOutcome.UNPLANNED}),
        ((session("ride"), session("swim", "SWIM", 45)),
         (event("bike"), event("water", "swimming", 2700)),
         {MatchStatus.MATCHED}, {ActivityExecutionOutcome.COMPLETED}),
        ((session("ride-1"), session("ride-2", "CADENCE")),
         (event(),), {MatchStatus.AMBIGUOUS}, {None}),
    ],
)
def test_adapter_preserves_reconciliation_scenarios(
    tmp_path, sessions, events, statuses, outcomes
):
    value, _, _, repository = adapter(tmp_path, plan(*sessions), events)
    result = value.execute(context())
    persisted = repository.get_by_id(result.artifact_ids[0])
    assert {item.match_status for item in persisted.items} == statuses
    assert {item.execution_outcome for item in persisted.items} == outcomes


def test_missing_previous_day_plan_is_truthful_skip(tmp_path):
    value, _, _, _ = adapter(tmp_path, None)
    outcome = value.execute(context())
    assert outcome.status is PhaseStatus.SKIPPED
    assert outcome.artifact_ids == ()
    assert outcome.reconciliations_created == 0
    assert outcome.warning_codes == (RECONCILIATION_PLAN_UNAVAILABLE,)


def test_identical_input_is_idempotent_and_changed_fact_appends(tmp_path):
    value, _, memory, repository = adapter(tmp_path, plan(session()), [event()])
    first = value.execute(context())
    second = value.execute(context())
    memory.events = [event("changed")]
    changed = value.execute(context())
    assert (first.reconciliations_created, second.reconciliations_created,
            changed.reconciliations_created) == (1, 0, 1)
    assert second.changed_state is False
    assert len(repository.list_for_date(CLOSED)) == 2


def test_current_date_and_legacy_events_do_not_enter_closed_date_result(tmp_path):
    current = event("current", start=datetime(2026, 8, 12, 8))
    legacy = event("legacy", event_type=AthleteMemoryEventType.WORKOUT_COMPLETED)
    value, _, _, repository = adapter(
        tmp_path, plan(session()), [current, legacy]
    )
    outcome = value.execute(context())
    persisted = repository.get_by_id(outcome.artifact_ids[0])
    assert persisted.activity_event_ids == ()
    assert persisted.items[0].execution_outcome is ActivityExecutionOutcome.SKIPPED
