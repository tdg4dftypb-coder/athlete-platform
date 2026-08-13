from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from application.athlete_assessment import (
    AthleteAssessment,
    AthleteAssessmentReason,
    AthleteAssessmentStatus,
    FatigueStatus,
)
from application.training_assessment import TrainingAssessment, TrainingAssessmentStatus
from plan_adaptation import (
    AdaptationAction,
    AdaptationContextBuilder,
    AdaptationContextWindow,
    AdaptationEvaluationStatus,
    AdaptationReasonCode,
    AdaptationWindow,
    DeterministicAdaptationPolicy,
    PlanAdaptationEvaluation,
    PlanRevisionProposal,
    PlanRevisionProposalBuilder,
    PlanRevisionValidationCode,
    PlanRevisionValidationError,
    PlanRevisionValidator,
    SessionAdaptationChange,
    TrainingPlanRevisionService,
)
from training_plan import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.reduction import reduced_duration_minutes_v1, reduced_target_tss_v1


D = date(2026, 8, 13)
NOW = datetime(2026, 8, 13, 8, tzinfo=timezone.utc)
LATER = NOW + timedelta(hours=1)
FINGERPRINT = "sha256:" + "c" * 64


def session(identifier, day, session_type="ENDURANCE", duration=60, target_tss=50.0, kind=PlannedSessionKind.TRAINING):
    return PlannedSession(
        identifier, day, kind,
        session_type if kind is PlannedSessionKind.TRAINING else None,
        duration if kind is PlannedSessionKind.TRAINING else 0,
        target_tss if kind is PlannedSessionKind.TRAINING else None,
        "MODERATE" if kind is PlannedSessionKind.TRAINING else None,
        3, ("baseline",),
    )


def source_plan(version=3, sessions=None, plan_id="plan-a"):
    if sessions is None:
        sessions = tuple(
            session(f"session-{offset}", D + timedelta(days=offset))
            for offset in range(1, 8)
        )
    return TrainingPlan(plan_id, D + timedelta(days=1), D + timedelta(days=7), version, NOW, tuple(sessions))


def change(identifier="session-1", day=1, action=AdaptationAction.SHORTEN, **targets):
    defaults = {"target_duration_minutes": 42} if action is AdaptationAction.SHORTEN else {}
    defaults.update(targets)
    return SessionAdaptationChange(
        identifier, D + timedelta(days=day), action,
        (AdaptationReasonCode.RECOVERY_PROTECTION,), **defaults,
    )


def evaluation(status=AdaptationEvaluationStatus.CHANGE_PROPOSED, changes=None, evaluated_at=NOW):
    if changes is None:
        changes = (change(),) if status is AdaptationEvaluationStatus.CHANGE_PROPOSED else ()
    return PlanAdaptationEvaluation(
        adaptation_id="adaptation-1",
        policy_version="1.0",
        status=status,
        evaluation_date=D,
        context_window=AdaptationContextWindow.canonical(D),
        mutation_window=AdaptationWindow.canonical(D),
        source_plan_id="plan-a",
        source_plan_version=3,
        proposed_changes=changes,
        reason_codes=(AdaptationReasonCode.RECOVERY_PROTECTION,) if changes else (),
        warning_codes=(),
        input_fingerprint=FINGERPRINT,
        evaluated_at=evaluated_at,
    )


def proposal(changes=None, **overrides):
    values = dict(
        proposal_id="proposal-1",
        policy_version="1.0",
        evaluation_date=D,
        source_plan_id="plan-a",
        source_plan_version=3,
        context_window=AdaptationContextWindow.canonical(D),
        mutation_window=AdaptationWindow.canonical(D),
        changes=(change(),) if changes is None else changes,
        reason_codes=(AdaptationReasonCode.RECOVERY_PROTECTION,),
        warning_codes=(),
        input_fingerprint=FINGERPRINT,
        evaluated_at=NOW,
    )
    values.update(overrides)
    return PlanRevisionProposal(**values)


def assert_error(code, function):
    with pytest.raises(PlanRevisionValidationError) as captured:
        function()
    assert captured.value.code is code


def test_no_change_evaluation_produces_no_proposal_or_plan_version():
    result = evaluation(AdaptationEvaluationStatus.NO_CHANGE)
    assert PlanRevisionProposalBuilder().build(result) is None


def test_change_evaluation_builds_deterministic_proposal_and_preserves_contract():
    builder = PlanRevisionProposalBuilder()
    first_evaluation = evaluation(evaluated_at=NOW)
    second_evaluation = replace(first_evaluation, evaluated_at=LATER)
    first = builder.build(first_evaluation)
    second = builder.build(second_evaluation)
    assert first.proposal_id == second.proposal_id
    assert first.evaluated_at != second.evaluated_at
    assert first.source_plan_id == "plan-a" and first.source_plan_version == 3
    assert first.changes == first_evaluation.proposed_changes
    assert first.reason_codes == first_evaluation.reason_codes
    assert first.warning_codes == first_evaluation.warning_codes
    assert first.input_fingerprint == first_evaluation.input_fingerprint


@pytest.mark.parametrize("candidate,code", [
    (source_plan(plan_id="plan-b"), PlanRevisionValidationCode.WRONG_SOURCE_PLAN),
    (source_plan(version=4), PlanRevisionValidationCode.STALE_SOURCE_VERSION),
    (source_plan(version=2), PlanRevisionValidationCode.SOURCE_VERSION_MISMATCH),
])
def test_source_identity_and_version_must_match(candidate, code):
    assert_error(code, lambda: PlanRevisionValidator().validate(proposal(), candidate))


def test_unknown_session_and_date_mismatch_are_rejected_by_stable_identity():
    unknown = proposal((change("unknown"),))
    assert_error(
        PlanRevisionValidationCode.UNKNOWN_SESSION,
        lambda: PlanRevisionValidator().validate(unknown, source_plan()),
    )
    wrong_date = proposal((change("session-1", day=2),))
    assert_error(
        PlanRevisionValidationCode.SESSION_DATE_MISMATCH,
        lambda: PlanRevisionValidator().validate(wrong_date, source_plan()),
    )


def test_shorten_rejects_rest_equal_longer_and_noncanonical_targets():
    rest_sessions = (
        session("rest", D + timedelta(days=1), kind=PlannedSessionKind.REST),
        *(session(f"session-{offset}", D + timedelta(days=offset)) for offset in range(2, 8)),
    )
    rest_change = proposal((change("rest"),))
    assert_error(
        PlanRevisionValidationCode.ILLEGAL_ACTION_FOR_SOURCE,
        lambda: PlanRevisionValidator().validate(rest_change, source_plan(sessions=rest_sessions)),
    )
    for target in (60, 75):
        invalid = proposal((change(target_duration_minutes=target),))
        assert_error(
            PlanRevisionValidationCode.NOT_SEMANTIC_REDUCTION,
            lambda invalid=invalid: PlanRevisionValidator().validate(invalid, source_plan()),
        )
    noncanonical = proposal((change(target_duration_minutes=30),))
    assert_error(
        PlanRevisionValidationCode.UNSUPPORTED_MATERIALIZATION,
        lambda: PlanRevisionValidator().validate(noncanonical, source_plan()),
    )
    with pytest.raises(ValueError, match="target_duration_minutes"):
        change(target_duration_minutes=0)


def test_one_minute_session_has_no_legal_canonical_shorten():
    sessions = (
        session("tiny", D + timedelta(days=1), duration=1),
        *(session(f"session-{offset}", D + timedelta(days=offset)) for offset in range(2, 8)),
    )
    tiny = proposal((change("tiny", target_duration_minutes=1),))
    assert_error(
        PlanRevisionValidationCode.NOT_SEMANTIC_REDUCTION,
        lambda: PlanRevisionValidator().validate(tiny, source_plan(sessions=sessions)),
    )


def test_canonical_reduction_preserves_legacy_float_truncation_and_factor_tss():
    assert reduced_duration_minutes_v1(90) == 62
    assert reduced_target_tss_v1(100) == pytest.approx(70.0)
    sessions = (
        session("long", D + timedelta(days=1), duration=90, target_tss=100.0),
        *(session(f"session-{offset}", D + timedelta(days=offset)) for offset in range(2, 8)),
    )
    long_change = proposal((change("long", target_duration_minutes=62),))
    revised = TrainingPlanRevisionService().apply(
        long_change, source_plan(sessions=sessions), generated_at=LATER,
    )
    assert revised.sessions[0].duration_minutes == 62
    assert revised.sessions[0].target_tss == pytest.approx(70.0)


@pytest.mark.parametrize("source_tss", [True, float("nan"), float("inf"), -1.0])
def test_target_tss_reduction_rejects_invalid_boundaries(source_tss):
    expected = TypeError if source_tss is True else ValueError
    with pytest.raises(expected):
        reduced_target_tss_v1(source_tss)


def test_target_tss_reduction_preserves_none_zero_and_numeric_type():
    assert reduced_target_tss_v1(None) is None
    assert reduced_target_tss_v1(0) == 0.0
    assert isinstance(reduced_target_tss_v1(100), float)


@pytest.mark.parametrize("unsupported", [
    change(action=AdaptationAction.REDUCE_INTENSITY, target_intensity="LOW"),
    change(action=AdaptationAction.DOWNGRADE, target_session_type="RECOVERY"),
    change(action=AdaptationAction.SKIP),
])
def test_actions_without_canonical_materialization_are_rejected(unsupported):
    candidate = proposal((unsupported,))
    assert_error(
        PlanRevisionValidationCode.UNSUPPORTED_MATERIALIZATION,
        lambda: PlanRevisionValidator().validate(candidate, source_plan()),
    )


def test_revision_keeps_plan_identity_increments_version_and_preserves_fields():
    source = source_plan()
    revised = TrainingPlanRevisionService().apply(proposal(), source, generated_at=LATER)
    assert revised.plan_id == source.plan_id
    assert revised.version == source.version + 1
    assert revised.start_date == source.start_date and revised.end_date == source.end_date
    assert revised.supersedes_plan_id == source.supersedes_plan_id
    assert revised.generated_at == LATER
    changed = next(item for item in revised.sessions if item.session_id == "session-1")
    original = next(item for item in source.sessions if item.session_id == "session-1")
    assert changed.session_id == original.session_id
    assert changed.duration_minutes == 42
    assert changed.target_tss == 35.0
    assert changed.intensity == original.intensity
    assert changed.priority == original.priority
    assert changed.rationale == original.rationale
    assert revised.sessions[1:] == source.sessions[1:]


def test_same_day_sibling_and_open_sport_are_preserved_independently():
    target = D + timedelta(days=1)
    sessions = (
        session("run", target, "RUNNING", 60, 40.0),
        session("swim", target, "SWIM", 45, 30.0),
        *(session(f"session-{offset}", D + timedelta(days=offset)) for offset in range(2, 8)),
    )
    source = source_plan(sessions=sessions)
    run_change = proposal((change("run"),))
    revised = TrainingPlanRevisionService().apply(run_change, source, generated_at=LATER)
    revised_run = next(item for item in revised.sessions if item.session_id == "run")
    revised_swim = next(item for item in revised.sessions if item.session_id == "swim")
    source_swim = next(item for item in source.sessions if item.session_id == "swim")
    assert revised_run.session_type == "RUNNING" and revised_run.duration_minutes == 42
    assert revised_swim == source_swim


def test_proposal_is_all_or_nothing_and_source_remains_untouched():
    source = source_plan()
    before = source.sessions
    mixed = proposal((change(), change("session-2", day=2, action=AdaptationAction.SKIP)))
    assert_error(
        PlanRevisionValidationCode.UNSUPPORTED_MATERIALIZATION,
        lambda: TrainingPlanRevisionService().apply(mixed, source, generated_at=LATER),
    )
    assert source.sessions == before and source.version == 3


def test_reapplication_to_revised_plan_is_stale():
    source = source_plan()
    candidate = proposal()
    revised = TrainingPlanRevisionService().apply(candidate, source, generated_at=LATER)
    assert_error(
        PlanRevisionValidationCode.STALE_SOURCE_VERSION,
        lambda: TrainingPlanRevisionService().apply(candidate, revised, generated_at=LATER),
    )


def test_revision_is_deterministic_except_for_explicit_audit_timestamp():
    source = source_plan()
    candidate = proposal()
    first = TrainingPlanRevisionService().apply(candidate, source, generated_at=NOW)
    second = TrainingPlanRevisionService().apply(candidate, source, generated_at=LATER)
    assert first.sessions == second.sessions
    assert first.plan_id == second.plan_id and first.version == second.version
    assert first.generated_at != second.generated_at


def adverse_assessment():
    training = TrainingAssessment(NOW, None, TrainingAssessmentStatus.NO_CLEAR_PATTERN, ())
    return AthleteAssessment(
        NOW, AthleteAssessmentStatus.CAUTION, training,
        (AthleteAssessmentReason.LOW_RECOVERY,), FatigueStatus.NORMAL,
    )


def context_for(plan, athlete_state):
    return AdaptationContextBuilder().build(
        evaluation_date=D,
        source_plan=plan,
        historical_planned_sessions=(),
        reconciliations=(),
        training_load=None,
        athlete_state=athlete_state,
        constraints=(),
        weekly_rhythm=None,
        built_at=NOW,
    )


def test_full_in_memory_vertical_slice_creates_real_n_plus_one():
    source = source_plan()
    context = context_for(source, adverse_assessment())
    evaluation_result = DeterministicAdaptationPolicy().evaluate(context, evaluated_at=NOW)
    candidate = PlanRevisionProposalBuilder().build(evaluation_result)
    revised = TrainingPlanRevisionService().apply(candidate, source, generated_at=LATER)
    assert evaluation_result.status is AdaptationEvaluationStatus.CHANGE_PROPOSED
    assert candidate.source_plan_version == 3
    assert revised.plan_id == source.plan_id and revised.version == 4
    assert revised.sessions[0].duration_minutes == 42


def test_healthy_vertical_slice_has_no_proposal_and_no_new_plan():
    source = source_plan()
    training = TrainingAssessment(NOW, None, TrainingAssessmentStatus.NO_CLEAR_PATTERN, ())
    healthy = AthleteAssessment(NOW, AthleteAssessmentStatus.STABLE, training, (), FatigueStatus.NORMAL)
    evaluation_result = DeterministicAdaptationPolicy().evaluate(context_for(source, healthy), evaluated_at=NOW)
    candidate = PlanRevisionProposalBuilder().build(evaluation_result)
    assert evaluation_result.status is AdaptationEvaluationStatus.NO_CHANGE
    assert candidate is None
    assert source.version == 3
