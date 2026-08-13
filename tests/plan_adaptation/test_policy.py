from dataclasses import replace
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
    AthleteAssessmentReason,
    AthleteAssessmentStatus,
    FatigueStatus,
)
from application.training_assessment import TrainingAssessment, TrainingAssessmentStatus
from application.training_plan_reconciliation import DailyTrainingReconciler
from plan_adaptation import (
    AdaptationAction,
    AdaptationContextBuilder,
    AdaptationEvaluationStatus,
    AdaptationReasonCode,
    AdaptationTrainingLoad,
    AdaptationWarningCode,
    DeterministicAdaptationPolicy,
    PlanAdaptationEvaluation,
)
from training_plan import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.reduction import DURATION_REDUCTION_FACTOR_V1


D = date(2026, 8, 13)
NOW = datetime(2026, 8, 13, 8, tzinfo=timezone.utc)
_DEFAULT_ASSESSMENT = object()


def session(
    identifier, day, session_type="ENDURANCE", duration=60,
    kind=PlannedSessionKind.TRAINING, priority=3,
):
    return PlannedSession(
        identifier, day, kind,
        session_type if kind is PlannedSessionKind.TRAINING else None,
        duration if kind is PlannedSessionKind.TRAINING else 0,
        50.0 if kind is PlannedSessionKind.TRAINING else None,
        "MODERATE" if kind is PlannedSessionKind.TRAINING else None,
        priority, ("baseline",),
    )


def assessment(status=AthleteAssessmentStatus.STABLE, reasons=(), fatigue=FatigueStatus.NORMAL):
    training = TrainingAssessment(NOW, None, TrainingAssessmentStatus.NO_CLEAR_PATTERN, ())
    return AthleteAssessment(NOW, status, training, reasons, fatigue)


def reconciliation(outcome=None):
    target = D - timedelta(days=1)
    if outcome is None:
        items = ()
    elif outcome is ActivityExecutionOutcome.UNPLANNED:
        items = (ReconciliationItem(
            MatchStatus.UNMATCHED_ACTIVITY,
            activity=ActivityReference("activity", "fit", "key"),
            execution_outcome=outcome,
        ),)
    else:
        status = MatchStatus.UNMATCHED_PLANNED if outcome is ActivityExecutionOutcome.SKIPPED else MatchStatus.MATCHED
        items = (ReconciliationItem(status, "history-session", execution_outcome=outcome),)
    return ReconciliationResult(
        "reconciliation", "sha256:" + "a" * 64, "1.0", target,
        "Europe/Warsaw", "history-plan", 1, True,
        ("history-session",),
        ("activity",) if outcome is ActivityExecutionOutcome.UNPLANNED else (),
        items, (), NOW,
    )


def context(
    *,
    athlete_state=_DEFAULT_ASSESSMENT,
    outcome=None,
    future_sessions=None,
    training_load=AdaptationTrainingLoad(300.0, 50.0, 60.0, -10.0),
):
    if athlete_state is _DEFAULT_ASSESSMENT:
        athlete_state = assessment()
    if future_sessions is None:
        future_sessions = tuple(
            session(f"future-{offset}", D + timedelta(days=offset))
            for offset in range(1, 8)
        )
    plan = TrainingPlan(
        "plan-29", D + timedelta(days=1), D + timedelta(days=7),
        5, NOW, tuple(future_sessions),
    )
    reconciliations = (reconciliation(outcome),) if outcome is not None else ()
    return AdaptationContextBuilder().build(
        evaluation_date=D,
        source_plan=plan,
        historical_planned_sessions=(),
        reconciliations=reconciliations,
        training_load=training_load,
        athlete_state=athlete_state,
        constraints=(),
        weekly_rhythm=None,
        built_at=NOW,
    )


def evaluate(ctx):
    return DeterministicAdaptationPolicy().evaluate(ctx, evaluated_at=NOW)


def adverse_assessment():
    return assessment(
        AthleteAssessmentStatus.CAUTION,
        (AthleteAssessmentReason.HIGH_FATIGUE,),
        FatigueStatus.HIGH,
    )


def test_policy_version_is_public_and_healthy_context_is_no_change():
    policy = DeterministicAdaptationPolicy()
    result = policy.evaluate(context(), evaluated_at=NOW)
    assert policy.policy_version == "1.0"
    assert result.policy_version == "1.0"
    assert result.status is AdaptationEvaluationStatus.NO_CHANGE
    assert result.proposed_changes == ()


def test_reduction_factor_has_one_neutral_owner_and_compatibility_alias():
    assert DURATION_REDUCTION_FACTOR_V1 == 0.70
    assert DeterministicAdaptationPolicy.REDUCTION_FACTOR == DURATION_REDUCTION_FACTOR_V1
    assert DailyTrainingReconciler.REDUCTION_FACTOR == DURATION_REDUCTION_FACTOR_V1


def test_completed_history_alone_preserves_future_plan():
    assert evaluate(context(outcome=ActivityExecutionOutcome.COMPLETED)).status is AdaptationEvaluationStatus.NO_CHANGE


@pytest.mark.parametrize("outcome", [
    ActivityExecutionOutcome.SKIPPED,
    ActivityExecutionOutcome.PARTIAL,
    ActivityExecutionOutcome.REPLACED,
    ActivityExecutionOutcome.UNPLANNED,
])
def test_execution_outcome_alone_never_creates_makeup_or_arbitrary_change(outcome):
    ctx = context(outcome=outcome)
    original_sessions = ctx.future_sessions
    result = evaluate(ctx)
    assert result.status is AdaptationEvaluationStatus.NO_CHANGE
    assert result.proposed_changes == ()
    assert ctx.future_sessions == original_sessions


def test_canonical_adverse_assessment_shortens_only_nearest_training_session():
    ctx = context(athlete_state=adverse_assessment())
    result = evaluate(ctx)
    assert result.status is AdaptationEvaluationStatus.CHANGE_PROPOSED
    assert len(result.proposed_changes) == 1
    change = result.proposed_changes[0]
    assert (change.session_id, change.action, change.target_duration_minutes) == (
        "future-1", AdaptationAction.SHORTEN, 42,
    )
    assert change.reason_codes == (AdaptationReasonCode.RECOVERY_PROTECTION,)


@pytest.mark.parametrize("reasons,fatigue", [
    ((AthleteAssessmentReason.LOW_RECOVERY,), FatigueStatus.NORMAL),
    ((AthleteAssessmentReason.HIGH_FATIGUE,), FatigueStatus.NORMAL),
    ((AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED,), FatigueStatus.HIGH),
])
def test_each_canonical_caution_safety_signal_triggers_protection(reasons, fatigue):
    adverse = assessment(AthleteAssessmentStatus.CAUTION, reasons, fatigue)
    assert evaluate(context(athlete_state=adverse)).status is AdaptationEvaluationStatus.CHANGE_PROPOSED


def test_non_safety_caution_does_not_trigger_stronger_intervention():
    attention_only = assessment(
        AthleteAssessmentStatus.CAUTION,
        (AthleteAssessmentReason.TRAINING_ATTENTION_REQUIRED,),
        FatigueStatus.NORMAL,
    )
    assert evaluate(context(athlete_state=attention_only)).status is AdaptationEvaluationStatus.NO_CHANGE


@pytest.mark.parametrize("reasons,fatigue", [
    ((AthleteAssessmentReason.LOW_RECOVERY,), FatigueStatus.NORMAL),
    ((AthleteAssessmentReason.HIGH_FATIGUE,), FatigueStatus.HIGH),
])
def test_safety_field_without_caution_status_does_not_trigger(reasons, fatigue):
    inconsistent = assessment(AthleteAssessmentStatus.STABLE, reasons, fatigue)
    assert evaluate(context(athlete_state=inconsistent)).status is AdaptationEvaluationStatus.NO_CHANGE


def test_rest_and_protected_recovery_are_never_converted_to_training():
    sessions = (
        session("rest", D + timedelta(days=1), kind=PlannedSessionKind.REST),
        session("training", D + timedelta(days=2)),
        *(session(f"future-{offset}", D + timedelta(days=offset)) for offset in range(3, 8)),
    )
    result = evaluate(context(athlete_state=adverse_assessment(), future_sessions=sessions))
    assert len(result.proposed_changes) == 1
    assert result.proposed_changes[0].session_id == "training"
    assert all(change.session_id != "rest" for change in result.proposed_changes)


def test_same_day_sessions_keep_independent_session_identity():
    sessions = (
        session("rest", D + timedelta(days=1), kind=PlannedSessionKind.REST),
        session("bike", D + timedelta(days=2), "BIKE", 90, priority=1),
        session("run", D + timedelta(days=2), "RUNNING", 45, priority=4),
        *(session(f"future-{offset}", D + timedelta(days=offset)) for offset in range(3, 8)),
    )
    result = evaluate(context(athlete_state=adverse_assessment(), future_sessions=sessions))
    assert tuple(change.session_id for change in result.proposed_changes) == ("bike",)
    assert result.proposed_changes[0].target_duration_minutes == 62


def test_same_day_equal_priority_is_not_resolved_arbitrarily_by_session_id():
    sessions = (
        session("rest", D + timedelta(days=1), kind=PlannedSessionKind.REST),
        session("aaa-bike", D + timedelta(days=2), "BIKE", 90, priority=2),
        session("zzz-run", D + timedelta(days=2), "RUNNING", 45, priority=2),
        *(session(f"future-{offset}", D + timedelta(days=offset)) for offset in range(3, 8)),
    )
    result = evaluate(context(athlete_state=adverse_assessment(), future_sessions=sessions))
    assert result.status is AdaptationEvaluationStatus.NO_CHANGE
    assert result.proposed_changes == ()
    assert AdaptationWarningCode.AMBIGUOUS_ADAPTATION_TARGET in result.warning_codes


def test_shortening_boundaries_skip_one_minute_and_never_emit_non_reduction():
    sessions = (
        session("one-minute", D + timedelta(days=1), duration=1),
        session("two-minutes", D + timedelta(days=2), duration=2),
        *(session(f"future-{offset}", D + timedelta(days=offset)) for offset in range(3, 8)),
    )
    result = evaluate(context(athlete_state=adverse_assessment(), future_sessions=sessions))
    assert len(result.proposed_changes) == 1
    change = result.proposed_changes[0]
    assert (change.session_id, change.target_duration_minutes) == ("two-minutes", 1)


@pytest.mark.parametrize("session_type", ["RUNNING", "UNKNOWN_FUTURE_SPORT"])
def test_open_session_types_are_supported_without_conversion(session_type):
    sessions = tuple(
        session(f"future-{offset}", D + timedelta(days=offset), session_type if offset == 1 else "ENDURANCE")
        for offset in range(1, 8)
    )
    ctx = context(athlete_state=adverse_assessment(), future_sessions=sessions)
    result = evaluate(ctx)
    assert result.proposed_changes[0].session_id == "future-1"
    assert result.proposed_changes[0].target_session_type is None
    assert ctx.future_sessions[0].session_type == session_type


def test_missing_assessment_is_not_adverse_and_warning_is_propagated():
    ctx = context(athlete_state=None)
    result = evaluate(ctx)
    assert result.status is AdaptationEvaluationStatus.NO_CHANGE
    assert AdaptationWarningCode.ATHLETE_ASSESSMENT_UNAVAILABLE in result.warning_codes
    assert result.reason_codes == ()


def test_all_context_quality_warnings_are_propagated_without_adverse_reasons():
    ctx = context(athlete_state=None, training_load=None)
    result = evaluate(ctx)
    assert result.warning_codes == ctx.warning_codes
    assert result.reason_codes == ()


def test_missing_load_does_not_block_independent_assessment_safety_rule():
    ctx = context(athlete_state=adverse_assessment(), training_load=None)
    result = evaluate(ctx)
    assert result.status is AdaptationEvaluationStatus.CHANGE_PROPOSED
    assert AdaptationWarningCode.TRAINING_LOAD_UNAVAILABLE in result.warning_codes


def test_same_context_has_deterministic_semantic_result_and_identity():
    ctx = context(athlete_state=adverse_assessment())
    first = DeterministicAdaptationPolicy().evaluate(ctx, evaluated_at=NOW)
    second = DeterministicAdaptationPolicy().evaluate(ctx, evaluated_at=NOW + timedelta(hours=1))
    assert first.adaptation_id == second.adaptation_id
    assert first.input_fingerprint == ctx.input_fingerprint == second.input_fingerprint
    assert first.proposed_changes == second.proposed_changes
    assert first.status is second.status
    assert first.evaluated_at != second.evaluated_at


def test_policy_returns_evaluation_only_and_does_not_mutate_context():
    ctx = context(athlete_state=adverse_assessment())
    before = ctx.future_sessions
    result = evaluate(ctx)
    assert isinstance(result, PlanAdaptationEvaluation)
    assert ctx.future_sessions == before
    assert not hasattr(result, "proposal_id")
