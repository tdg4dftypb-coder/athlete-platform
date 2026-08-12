from datetime import date, datetime, timedelta, timezone

import pytest

from activity_reconciliation import (
    ActivityExecutionOutcome, ActivitySessionReconciler, MatchStatus,
    ReplacementEvidence,
)
from activity_reconciliation.persistence import DuckDbReconciliationResultRepository
from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan


TARGET = date(2026, 8, 16)
NOW = datetime(2026, 8, 17, 6, 0, tzinfo=timezone.utc)


def session(session_id, session_type="ENDURANCE", minutes=60, kind=PlannedSessionKind.TRAINING):
    return PlannedSession(
        session_id, TARGET, kind, None if kind is PlannedSessionKind.REST else session_type,
        0 if kind is PlannedSessionKind.REST else minutes,
        0.0 if kind is PlannedSessionKind.REST else 50.0,
        None, 2, (),
    )


def plan(*sessions, version=1):
    return TrainingPlan("plan", TARGET, TARGET, version, NOW, tuple(sessions))


def activity(
    event_id, sport="cycling", duration=3600, start=None,
    event_type=AthleteMemoryEventType.ACTIVITY_RECORDED, schema_version=1,
):
    start = start or datetime(2026, 8, 16, 10, 0)
    return AthleteMemoryEvent(
        event_id, start + timedelta(seconds=duration or 0), event_type,
        "fit_file", f"sha256:{event_id}", schema_version,
        {"activity": {"start": start.isoformat(), "sport": sport, "duration": duration}},
    )


def reconcile(training_plan, activities=(), *, finalized=True, replacements=(), evaluated_at=NOW):
    return ActivitySessionReconciler().reconcile(
        training_plan, tuple(activities), TARGET, finalized, evaluated_at,
        replacement_evidence=tuple(replacements),
    )


@pytest.mark.parametrize(
    ("session_type", "sport"),
    [("ENDURANCE", "cycling"), ("SWIM", "swimming")],
)
def test_unique_sport_match_is_completed(session_type, sport):
    result = reconcile(plan(session("s", session_type)), [activity("a", sport)])
    item = result.items[0]
    assert item.match_status is MatchStatus.MATCHED
    assert item.execution_outcome is ActivityExecutionOutcome.COMPLETED
    assert item.completion_percent == 100.0
    assert item.activity.source_key == "sha256:a"


def test_two_distinct_sports_match_independently_and_ignore_input_order():
    training_plan = plan(session("ride", "ENDURANCE"), session("swim", "SWIM", 45))
    activities = [activity("water", "swimming", 2700), activity("bike", "cycling")]
    first = reconcile(training_plan, activities)
    second = reconcile(training_plan, reversed(activities))
    pairs = {(i.planned_session_id, i.activity.event_id) for i in first.items}
    assert pairs == {("ride", "bike"), ("swim", "water")}
    assert first.input_fingerprint == second.input_fingerprint
    assert first.items == second.items


@pytest.mark.parametrize(
    ("sessions", "activities"),
    [
        ((session("a"), session("b", "CADENCE")), (activity("x"), activity("y"))),
        ((session("a"), session("b", "CADENCE")), (activity("x"),)),
        ((session("a"),), (activity("x"), activity("y"))),
    ],
)
def test_many_candidate_relationships_are_ambiguous_without_guessing(sessions, activities):
    result = reconcile(plan(*sessions), activities)
    assert result.items
    assert all(item.match_status is MatchStatus.AMBIGUOUS for item in result.items)
    assert all(item.execution_outcome is None for item in result.items)


@pytest.mark.parametrize("sport", ["swimming", "unknown", None])
def test_incompatible_or_unknown_sport_is_not_guessed(sport):
    result = reconcile(plan(session("ride")), [activity("a", sport)])
    outcomes = {item.execution_outcome for item in result.items}
    assert ActivityExecutionOutcome.SKIPPED in outcomes
    assert ActivityExecutionOutcome.UNPLANNED in outcomes


def test_rest_has_no_outcome_and_activity_is_unplanned():
    result = reconcile(plan(session("rest", kind=PlannedSessionKind.REST)), [activity("a")])
    rest_item = next(item for item in result.items if item.planned_session_id == "rest")
    activity_item = next(item for item in result.items if item.activity is not None)
    assert rest_item.execution_outcome is None
    assert rest_item.reason_codes == ("intentional_rest",)
    assert activity_item.execution_outcome is ActivityExecutionOutcome.UNPLANNED


@pytest.mark.parametrize(
    ("duration", "outcome", "percent"),
    [(5400, ActivityExecutionOutcome.COMPLETED, 100.0),
     (3240, ActivityExecutionOutcome.COMPLETED, 90.0),
     (3239, ActivityExecutionOutcome.PARTIAL, pytest.approx(89.972222))],
)
def test_duration_classifies_execution_after_identity_match(duration, outcome, percent):
    item = reconcile(plan(session("s")), [activity("a", duration=duration)]).items[0]
    assert item.execution_outcome is outcome
    assert item.completion_percent == percent


def test_missing_duration_retains_match_with_warning_and_no_outcome():
    item = reconcile(plan(session("s")), [activity("a", duration=None)]).items[0]
    assert item.match_status is MatchStatus.MATCHED
    assert item.execution_outcome is None
    assert item.completion_percent is None
    assert item.warning_codes == ("activity_duration_missing",)


def test_skipped_requires_explicit_finalization():
    open_item = reconcile(plan(session("s")), finalized=False).items[0]
    closed_item = reconcile(plan(session("s")), finalized=True).items[0]
    assert open_item.execution_outcome is None
    assert "target_date_not_finalized" in open_item.reason_codes
    assert closed_item.execution_outcome is ActivityExecutionOutcome.SKIPPED


def test_explicit_replacement_is_supported_but_never_inferred():
    training_plan = plan(session("swim", "SWIM"))
    recorded = activity("ride", "cycling")
    automatic = reconcile(training_plan, [recorded])
    assert ActivityExecutionOutcome.REPLACED not in {i.execution_outcome for i in automatic.items}
    explicit = reconcile(training_plan, [recorded], replacements=[
        ReplacementEvidence("swim", "ride", "athlete_confirmation", "manual_replacement")
    ])
    assert explicit.items[0].execution_outcome is ActivityExecutionOutcome.REPLACED


def test_invalid_replacement_references_fail_clearly():
    with pytest.raises(ValueError, match="unknown target-date input"):
        reconcile(plan(session("s")), [activity("a")], replacements=[
            ReplacementEvidence("missing", "a", "manual", "replacement")
        ])


def test_local_date_uses_wall_time_for_naive_and_timezone_conversion_for_aware():
    training_plan = plan(session("s"))
    naive = activity("naive", start=datetime(2026, 8, 16, 0, 30))
    aware = activity("aware", start=datetime(2026, 8, 15, 22, 30, tzinfo=timezone.utc))
    result = reconcile(training_plan, [aware, naive])
    assert result.activity_event_ids == ("aware", "naive")
    assert all(item.match_status is MatchStatus.AMBIGUOUS for item in result.items)


def test_legacy_workout_completed_is_ignored_not_double_counted():
    canonical = activity("canonical")
    legacy = activity("legacy", event_type=AthleteMemoryEventType.WORKOUT_COMPLETED)
    result = reconcile(plan(session("s")), [legacy, canonical])
    assert result.activity_event_ids == ("canonical",)
    assert len(result.items) == 1


def test_append_only_repository_is_idempotent_and_preserves_changed_inputs(tmp_path):
    repository = DuckDbReconciliationResultRepository(tmp_path / "reconciliation.duckdb")
    training_plan = plan(session("s"))
    first = reconcile(training_plan, [activity("a")])
    same_input_later = reconcile(training_plan, [activity("a")], evaluated_at=NOW + timedelta(hours=1))
    changed_activity = reconcile(training_plan, [activity("b")])
    changed_plan = reconcile(plan(session("s"), version=2), [activity("a")])

    for result in (first, same_input_later, changed_activity, changed_plan):
        repository.save(result)

    assert first.input_fingerprint == same_input_later.input_fingerprint
    assert repository.get_by_fingerprint(first.input_fingerprint) == first
    assert len(repository.list_for_date(TARGET)) == 3


@pytest.mark.parametrize(
    "changed_session",
    [
        session("s", "SWIM"),
        session("s", "ENDURANCE", minutes=90),
        PlannedSession(
            "s", TARGET, PlannedSessionKind.TRAINING, "ENDURANCE", 60,
            75.0, "HIGH", 5, ("Changed rationale",),
        ),
    ],
)
def test_changed_planned_session_semantics_change_fingerprint(changed_session):
    baseline = reconcile(plan(session("s")), [activity("a")])
    changed = reconcile(plan(changed_session), [activity("a")])
    assert changed.input_fingerprint != baseline.input_fingerprint


def test_evaluation_time_is_not_part_of_fingerprint():
    training_plan = plan(session("s"))
    first = reconcile(training_plan, [activity("a")], evaluated_at=NOW)
    later = reconcile(
        training_plan, [activity("a")], evaluated_at=NOW + timedelta(hours=4)
    )
    assert first.input_fingerprint == later.input_fingerprint


def test_activity_schema_version_is_part_of_fingerprint():
    training_plan = plan(session("s"))
    first = reconcile(training_plan, [activity("a", schema_version=1)])
    changed = reconcile(training_plan, [activity("a", schema_version=2)])
    assert first.input_fingerprint != changed.input_fingerprint


def test_changed_session_semantics_append_separate_persisted_result(tmp_path):
    repository = DuckDbReconciliationResultRepository(tmp_path / "semantic.duckdb")
    baseline = reconcile(plan(session("s")), [activity("a")])
    same_input_later = reconcile(
        plan(session("s")), [activity("a")], evaluated_at=NOW + timedelta(hours=1)
    )
    changed = reconcile(plan(session("s", minutes=90)), [activity("a")])

    repository.save(baseline)
    repository.save(same_input_later)
    repository.save(changed)

    assert baseline.input_fingerprint == same_input_later.input_fingerprint
    assert changed.input_fingerprint != baseline.input_fingerprint
    assert len(repository.list_for_date(TARGET)) == 2
