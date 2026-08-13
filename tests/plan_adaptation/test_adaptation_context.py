from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone

import pytest

from activity_reconciliation import (
    ActivityExecutionOutcome,
    ActivityReference,
    MatchStatus,
    ReconciliationItem,
    ReconciliationResult,
)
from application.athlete_assessment import (
    AthleteAssessment,
    AthleteAssessmentStatus,
    FatigueStatus,
)
from application.training_assessment import TrainingAssessment, TrainingAssessmentStatus
from plan_adaptation import (
    AdaptationConstraint,
    AdaptationConstraintType,
    AdaptationContextBuildError,
    AdaptationContextBuilder,
    AdaptationTrainingLoad,
    AdaptationWarningCode,
    WeeklyRhythm,
    WeeklyRhythmDay,
    WeeklyRhythmSlot,
)
from training_plan import PlannedSession, PlannedSessionKind, TrainingPlan, Weekday


D = date(2026, 8, 13)
BUILT_AT = datetime(2026, 8, 13, 8, tzinfo=timezone.utc)


def session(identifier, target_date, session_type="ENDURANCE", duration=60):
    return PlannedSession(
        identifier, target_date, PlannedSessionKind.TRAINING, session_type,
        duration, 50.0, "MODERATE", 3, ("planned",),
    )


def source_plan(order_reversed=False):
    sessions = []
    for offset in range(1, 8):
        target = D + timedelta(days=offset)
        sessions.append(session(f"future-{offset}", target))
    sessions.append(session("future-swim", D + timedelta(days=3), "SWIM", 40))
    values = tuple(reversed(sessions)) if order_reversed else tuple(sessions)
    return TrainingPlan("plan-29", D + timedelta(days=1), D + timedelta(days=7), 4, BUILT_AT, values)


def reconciliation(target_date, items=(), finalized=True):
    return ReconciliationResult(
        reconciliation_id=f"reconciliation-{target_date}",
        input_fingerprint="sha256:" + "b" * 64,
        policy_version="1.0",
        target_local_date=target_date,
        timezone_name="Europe/Warsaw",
        plan_id="historical-plan",
        plan_version=2,
        finalized=finalized,
        planned_session_ids=tuple(
            item.planned_session_id for item in items if item.planned_session_id is not None
        ),
        activity_event_ids=tuple(
            item.activity.event_id for item in items if item.activity is not None
        ),
        items=items,
        replacement_evidence=(),
        evaluated_at=BUILT_AT,
    )


def complete_reconciliations(special=()):
    by_date = {item.target_local_date: item for item in special}
    return tuple(
        by_date.get(D - timedelta(days=offset), reconciliation(D - timedelta(days=offset)))
        for offset in range(7, -1, -1)
    )


def rhythm(reverse=False):
    days = []
    for weekday in Weekday:
        if weekday is Weekday.SUNDAY:
            slots = (
                WeeklyRhythmSlot(PlannedSessionKind.TRAINING, "SWIM"),
                WeeklyRhythmSlot(PlannedSessionKind.TRAINING, "ENDURANCE", fixed=True),
            )
        elif weekday in (Weekday.MONDAY, Weekday.WEDNESDAY):
            slots = (WeeklyRhythmSlot(PlannedSessionKind.REST, None),)
        else:
            slots = (WeeklyRhythmSlot(PlannedSessionKind.TRAINING, "CROSSFIT" if weekday is Weekday.THURSDAY else "ENDURANCE"),)
        days.append(WeeklyRhythmDay(weekday, slots, protected_recovery=weekday is Weekday.MONDAY))
    return WeeklyRhythm("rhythm-1", tuple(reversed(days)) if reverse else tuple(days))


def assessment():
    training = TrainingAssessment(BUILT_AT, None, TrainingAssessmentStatus.NO_CLEAR_PATTERN, ())
    return AthleteAssessment(BUILT_AT, AthleteAssessmentStatus.STABLE, training, (), FatigueStatus.NORMAL)


def build(**overrides):
    values = dict(
        evaluation_date=D,
        source_plan=source_plan(),
        historical_planned_sessions=(),
        reconciliations=complete_reconciliations(),
        training_load=AdaptationTrainingLoad(300.0, 50.0, 60.0, -10.0),
        athlete_state=assessment(),
        constraints=(AdaptationConstraint("monday-protected", AdaptationConstraintType.PROTECTED_RECOVERY_DAY, weekday=Weekday.MONDAY),),
        weekly_rhythm=rhythm(),
        built_at=BUILT_AT,
    )
    values.update(overrides)
    return AdaptationContextBuilder().build(**values)


def test_context_has_exact_windows_and_eight_historical_days():
    context = build()
    assert tuple(day.day for day in context.historical_days) == tuple(
        D - timedelta(days=offset) for offset in range(7, -1, -1)
    )
    assert (context.mutation_window.mutation_start, context.mutation_window.mutation_end) == (
        D + timedelta(days=1), D + timedelta(days=7),
    )


def test_source_plan_must_cover_complete_future_window():
    short = TrainingPlan(
        "short", D + timedelta(days=1), D + timedelta(days=6), 1, BUILT_AT,
        tuple(session(f"s-{offset}", D + timedelta(days=offset)) for offset in range(1, 7)),
    )
    with pytest.raises(AdaptationContextBuildError, match="complete D\\+1 through D\\+7"):
        build(source_plan=short)


def test_history_supports_empty_single_and_multiple_planned_sessions():
    crossfit = session("crossfit", D - timedelta(days=2), "CROSSFIT")
    endurance = session("endurance", D - timedelta(days=1), "ENDURANCE")
    swim = session("swim", D - timedelta(days=1), "SWIM")
    context = build(historical_planned_sessions=(swim, crossfit, endurance))
    assert context.historical_days[0].planned_sessions == ()
    assert tuple(item.session_id for item in context.historical_days[5].planned_sessions) == ("crossfit",)
    assert tuple(item.session_id for item in context.historical_days[6].planned_sessions) == ("endurance", "swim")


def test_history_preserves_every_canonical_outcome_none_and_ambiguity():
    activity = ActivityReference("activity-unplanned", "fit", "key")
    items = (
        ReconciliationItem(MatchStatus.MATCHED, "completed", execution_outcome=ActivityExecutionOutcome.COMPLETED),
        ReconciliationItem(MatchStatus.MATCHED, "partial", execution_outcome=ActivityExecutionOutcome.PARTIAL),
        ReconciliationItem(MatchStatus.UNMATCHED_PLANNED, "skipped", execution_outcome=ActivityExecutionOutcome.SKIPPED),
        ReconciliationItem(MatchStatus.MATCHED, "replaced", activity, execution_outcome=ActivityExecutionOutcome.REPLACED),
        ReconciliationItem(MatchStatus.UNMATCHED_ACTIVITY, activity=activity, execution_outcome=ActivityExecutionOutcome.UNPLANNED),
        ReconciliationItem(MatchStatus.MATCHED, "unknown", execution_outcome=None),
        ReconciliationItem(MatchStatus.AMBIGUOUS, candidate_session_ids=("b", "a"), candidate_activity_event_ids=("z", "y")),
    )
    target = D - timedelta(days=1)
    context = build(reconciliations=complete_reconciliations((reconciliation(target, items),)))
    preserved = context.historical_days[6].reconciliation.items
    assert {item.execution_outcome for item in preserved} == {
        ActivityExecutionOutcome.COMPLETED, ActivityExecutionOutcome.PARTIAL,
        ActivityExecutionOutcome.SKIPPED, ActivityExecutionOutcome.REPLACED,
        ActivityExecutionOutcome.UNPLANNED, None,
    }
    assert AdaptationWarningCode.RECONCILIATION_AMBIGUOUS in context.warning_codes
    assert AdaptationWarningCode.RECONCILIATION_INCOMPLETE in context.warning_codes


def test_missing_reconciliation_is_preserved_and_warned():
    context = build(reconciliations=complete_reconciliations()[:-1])
    assert context.historical_days[-1].reconciliation is None
    assert AdaptationWarningCode.RECONCILIATION_UNAVAILABLE in context.warning_codes


def test_future_sessions_include_all_seven_days_and_same_day_identity():
    context = build()
    assert {item.date for item in context.future_sessions} == {D + timedelta(days=offset) for offset in range(1, 8)}
    same_day = tuple(item for item in context.future_sessions if item.date == D + timedelta(days=3))
    assert tuple(item.session_id for item in same_day) == ("future-3", "future-swim")


def test_training_load_keeps_missing_metrics_as_none_and_reports_quality():
    partial = build(training_load=AdaptationTrainingLoad(recent_training_load_7d=250.0))
    assert partial.training_load.ctl is None
    assert AdaptationWarningCode.TRAINING_LOAD_PARTIAL in partial.warning_codes
    unavailable = build(training_load=None)
    assert unavailable.training_load is None
    assert AdaptationWarningCode.TRAINING_LOAD_UNAVAILABLE in unavailable.warning_codes


def test_training_load_rejects_invalid_values_without_turning_missing_into_zero():
    with pytest.raises(ValueError, match="finite"):
        AdaptationTrainingLoad(ctl=float("nan"))
    with pytest.raises(ValueError, match="ctl must be >= 0"):
        AdaptationTrainingLoad(ctl=-1)
    load = AdaptationTrainingLoad(recent_training_load_7d=None)
    assert load.recent_training_load_7d is None
    with pytest.raises(TypeError, match="numeric"):
        AdaptationTrainingLoad(atl=True)
    missing = build(training_load=AdaptationTrainingLoad(recent_training_load_7d=None))
    zero = build(training_load=AdaptationTrainingLoad(recent_training_load_7d=0))
    assert missing.input_fingerprint != zero.input_fingerprint


def test_assessment_rhythm_and_constraints_can_be_explicitly_unavailable():
    context = build(athlete_state=None, weekly_rhythm=None, constraints=None)
    assert context.athlete_state is None and context.weekly_rhythm is None and context.constraints == ()
    assert {
        AdaptationWarningCode.ATHLETE_ASSESSMENT_UNAVAILABLE,
        AdaptationWarningCode.WEEKLY_RHYTHM_UNAVAILABLE,
        AdaptationWarningCode.ATHLETE_CONSTRAINTS_UNAVAILABLE,
    }.issubset(context.warning_codes)


def test_weekly_rhythm_represents_multi_session_fixed_and_protected_semantics():
    context = build()
    monday = context.weekly_rhythm.days[Weekday.MONDAY]
    sunday = context.weekly_rhythm.days[Weekday.SUNDAY]
    assert monday.protected_recovery is True
    assert tuple(slot.session_type for slot in sunday.slots) == ("ENDURANCE", "SWIM")
    assert sunday.slots[0].fixed is True


def test_context_is_sport_agnostic_for_future_running_sessions():
    plan = source_plan()
    running = session("future-run", D + timedelta(days=3), "RUNNING", 45)
    plan = replace(plan, sessions=tuple(
        running if item.session_id == "future-3" else item for item in plan.sessions
    ))
    historical_run = session("history-run", D - timedelta(days=1), "RUNNING", 35)
    running_constraint = AdaptationConstraint(
        "running-fixed", AdaptationConstraintType.FIXED_SESSION,
        session_type="RUNNING",
    )
    context = build(
        source_plan=plan,
        historical_planned_sessions=(historical_run,),
        constraints=(running_constraint,),
    )
    assert any(item.session_type == "RUNNING" for item in context.future_sessions)
    assert context.historical_days[6].planned_sessions[0].session_type == "RUNNING"
    assert context.constraints[0].session_type == "RUNNING"


def test_full_plan_coverage_allows_canonical_rest_day():
    plan = source_plan()
    rest_date = D + timedelta(days=4)
    rest = PlannedSession(
        "future-rest", rest_date, PlannedSessionKind.REST, None,
        0, None, None, 1, ("recovery",),
    )
    plan = replace(plan, sessions=tuple(
        rest if item.date == rest_date else item for item in plan.sessions
    ))
    context = build(source_plan=plan)
    assert tuple(item for item in context.future_sessions if item.date == rest_date) == (rest,)


def test_source_collection_order_does_not_change_context_or_fingerprint():
    historical = (
        session("swim-history", D - timedelta(days=1), "SWIM"),
        session("crossfit-history", D - timedelta(days=2), "CROSSFIT"),
    )
    reconciliations = complete_reconciliations()
    constraints = (
        AdaptationConstraint("z", AdaptationConstraintType.FIXED_SESSION, session_type="SWIM"),
        AdaptationConstraint("a", AdaptationConstraintType.PROTECTED_RECOVERY_DAY, weekday=Weekday.MONDAY),
    )
    first = build(historical_planned_sessions=historical, reconciliations=reconciliations, constraints=constraints)
    second = build(
        source_plan=source_plan(order_reversed=True),
        historical_planned_sessions=tuple(reversed(historical)),
        reconciliations=tuple(reversed(reconciliations)),
        constraints=tuple(reversed(constraints)),
        weekly_rhythm=rhythm(reverse=True),
    )
    assert replace(first, built_at=second.built_at) == second
    assert first.input_fingerprint == second.input_fingerprint


def test_built_at_is_not_fingerprint_input_and_context_is_immutable():
    first = build()
    second = build(built_at=BUILT_AT + timedelta(hours=2))
    assert first.input_fingerprint == second.input_fingerprint
    assert isinstance(first.historical_days, tuple)
    with pytest.raises(FrozenInstanceError):
        first.source_plan_version = 5


def test_assessment_audit_timestamps_are_not_fingerprint_input():
    first_assessment = assessment()
    later = BUILT_AT + timedelta(hours=3)
    second_assessment = replace(
        first_assessment,
        as_of=later,
        training_assessment=replace(first_assessment.training_assessment, as_of=later),
    )
    first = build(athlete_state=first_assessment)
    second = build(athlete_state=second_assessment)
    assert first.athlete_state.as_of != second.athlete_state.as_of
    assert first.input_fingerprint == second.input_fingerprint


def test_reconciliation_item_and_nested_identifier_order_is_deterministic():
    target = D - timedelta(days=1)
    activity_a = ActivityReference("activity-a", "fit", "a")
    activity_b = ActivityReference("activity-b", "fit", "b")
    first_item = ReconciliationItem(
        MatchStatus.AMBIGUOUS,
        candidate_session_ids=("session-b", "session-a"),
        candidate_activity_event_ids=("activity-b", "activity-a"),
        reason_codes=("z-reason", "a-reason"),
        warning_codes=("z-warning", "a-warning"),
    )
    second_item = ReconciliationItem(
        MatchStatus.UNMATCHED_ACTIVITY,
        activity=activity_b,
        execution_outcome=ActivityExecutionOutcome.UNPLANNED,
    )
    first_result = replace(
        reconciliation(target, (first_item, second_item)),
        activity_event_ids=(activity_a.event_id, activity_b.event_id),
    )
    second_result = replace(
        first_result,
        planned_session_ids=tuple(reversed(first_result.planned_session_ids)),
        activity_event_ids=tuple(reversed(first_result.activity_event_ids)),
        items=(second_item, replace(
            first_item,
            candidate_session_ids=tuple(reversed(first_item.candidate_session_ids)),
            candidate_activity_event_ids=tuple(reversed(first_item.candidate_activity_event_ids)),
            reason_codes=tuple(reversed(first_item.reason_codes)),
            warning_codes=tuple(reversed(first_item.warning_codes)),
        )),
    )
    first = build(reconciliations=complete_reconciliations((first_result,)))
    second = build(reconciliations=complete_reconciliations((second_result,)))
    assert first == second
    assert first.input_fingerprint == second.input_fingerprint


def test_builder_scope_exposes_context_not_policy_or_proposal():
    context = build()
    assert not hasattr(context, "changes")
    assert not hasattr(context, "action")
