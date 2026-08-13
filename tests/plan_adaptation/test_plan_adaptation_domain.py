from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone

import pytest

from plan_adaptation import (
    AdaptationAction,
    AdaptationContextWindow,
    AdaptationEvaluationStatus,
    AdaptationReasonCode,
    AdaptationWarningCode,
    AdaptationWindow,
    PlanAdaptationEvaluation,
    PlanRevisionProposal,
    SessionAdaptationChange,
)


D = date(2026, 8, 13)
NOW = datetime(2026, 8, 13, 7, 0, tzinfo=timezone.utc)
FINGERPRINT = "sha256:" + "a" * 64
REASONS = (AdaptationReasonCode.RECOVERY_PROTECTION,)


def change(action=AdaptationAction.SHORTEN, session_id="session-a", day=1, **targets):
    defaults = {"target_duration_minutes": 30} if action is AdaptationAction.SHORTEN else {}
    defaults.update(targets)
    return SessionAdaptationChange(session_id, D + timedelta(days=day), action, REASONS, **defaults)


def snapshot_fields(changes):
    return dict(
        policy_version="29.1-contract-v1",
        evaluation_date=D,
        source_plan_id="plan-1",
        source_plan_version=3,
        context_window=AdaptationContextWindow.canonical(D),
        mutation_window=AdaptationWindow.canonical(D),
        reason_codes=REASONS,
        warning_codes=(AdaptationWarningCode.CONTEXT_INCOMPLETE,),
        input_fingerprint=FINGERPRINT,
        evaluated_at=NOW,
        changes=changes,
    )


def test_canonical_windows_make_v1_boundaries_explicit():
    context = AdaptationContextWindow.canonical(D)
    mutation = AdaptationWindow.canonical(D)
    assert (context.context_start, context.context_end) == (D - timedelta(days=7), D)
    assert (mutation.mutation_start, mutation.mutation_end) == (D + timedelta(days=1), D + timedelta(days=7))


@pytest.mark.parametrize("start,end,message", [
    (D, D + timedelta(days=1), "after evaluation_date"),
    (D - timedelta(days=1), D + timedelta(days=1), "after evaluation_date"),
    (D + timedelta(days=2), D + timedelta(days=1), "on or after mutation_start"),
    (D + timedelta(days=1), D + timedelta(days=8), "D\\+7 horizon"),
    (D + timedelta(days=2), D + timedelta(days=7), "equal D\\+1"),
    (D + timedelta(days=1), D + timedelta(days=6), "equal D\\+7"),
])
def test_invalid_mutation_windows_are_rejected(start, end, message):
    with pytest.raises(ValueError, match=message):
        AdaptationWindow(D, start, end)


def test_invalid_context_window_relationships_are_rejected():
    with pytest.raises(ValueError, match="on or before"):
        AdaptationContextWindow(D, D, D - timedelta(days=1))
    with pytest.raises(ValueError, match="equal evaluation_date"):
        AdaptationContextWindow(D, D - timedelta(days=7), D - timedelta(days=1))
    with pytest.raises(ValueError, match="D-7"):
        AdaptationContextWindow(D, D - timedelta(days=8), D)
    with pytest.raises(ValueError, match="equal D-7"):
        AdaptationContextWindow(D, D - timedelta(days=6), D)


@pytest.mark.parametrize("candidate", [
    SessionAdaptationChange("keep", D + timedelta(days=1), AdaptationAction.KEEP, REASONS),
    SessionAdaptationChange("short", D + timedelta(days=1), AdaptationAction.SHORTEN, REASONS, target_duration_minutes=25),
    SessionAdaptationChange("reduce", D + timedelta(days=1), AdaptationAction.REDUCE_INTENSITY, REASONS, target_intensity="easy"),
    SessionAdaptationChange("down", D + timedelta(days=1), AdaptationAction.DOWNGRADE, REASONS, target_session_type="recovery"),
    SessionAdaptationChange("skip", D + timedelta(days=1), AdaptationAction.SKIP, REASONS),
])
def test_all_v1_actions_have_valid_strongly_typed_representations(candidate):
    assert isinstance(candidate.action, AdaptationAction)


@pytest.mark.parametrize("action,targets,message", [
    (AdaptationAction.KEEP, {"target_duration_minutes": 10}, "must not carry"),
    (AdaptationAction.SKIP, {"target_intensity": "EASY"}, "must not carry"),
    (AdaptationAction.SHORTEN, {}, "requires target_duration_minutes"),
    (AdaptationAction.SHORTEN, {"target_duration_minutes": 0}, "requires target_duration_minutes"),
    (AdaptationAction.SHORTEN, {"target_duration_minutes": True}, "requires target_duration_minutes"),
    (AdaptationAction.SHORTEN, {"target_duration_minutes": 10, "target_intensity": "EASY"}, "accepts only"),
    (AdaptationAction.REDUCE_INTENSITY, {}, "requires target_intensity"),
    (AdaptationAction.REDUCE_INTENSITY, {"target_intensity": "EASY", "target_duration_minutes": 10}, "accepts only"),
    (AdaptationAction.DOWNGRADE, {}, "requires target_session_type"),
    (AdaptationAction.DOWNGRADE, {"target_session_type": "RECOVERY", "target_intensity": "EASY"}, "accepts only"),
])
def test_contradictory_action_targets_are_rejected(action, targets, message):
    with pytest.raises(ValueError, match=message):
        SessionAdaptationChange("s", D + timedelta(days=1), action, REASONS, **targets)


def test_unsupported_actions_and_mutable_reason_collections_are_rejected():
    with pytest.raises(TypeError, match="AdaptationAction"):
        SessionAdaptationChange("s", D + timedelta(days=1), "MOVE", REASONS)
    with pytest.raises(TypeError, match="tuple"):
        SessionAdaptationChange("s", D + timedelta(days=1), AdaptationAction.KEEP, list(REASONS))
    assert {action.value for action in AdaptationAction} == {"KEEP", "SHORTEN", "REDUCE_INTENSITY", "DOWNGRADE", "SKIP"}


def test_valid_proposal_normalizes_order_and_supports_same_day_sessions():
    later_id = change(session_id="swim", day=3)
    earlier_id = change(AdaptationAction.SKIP, session_id="endurance", day=3)
    proposal = PlanRevisionProposal(proposal_id="proposal-1", **snapshot_fields((later_id, earlier_id)))
    assert tuple(item.session_id for item in proposal.changes) == ("endurance", "swim")


def test_proposal_rejects_duplicates_outside_window_and_no_semantic_change():
    with pytest.raises(ValueError, match="duplicate session_id"):
        PlanRevisionProposal(proposal_id="p", **snapshot_fields((change(), change(day=2))))
    for day in (0, -1, 8):
        with pytest.raises(ValueError, match="inside the mutation window"):
            PlanRevisionProposal(proposal_id="p", **snapshot_fields((change(day=day),)))
    keep = change(AdaptationAction.KEEP)
    with pytest.raises(ValueError, match="semantic session change"):
        PlanRevisionProposal(proposal_id="p", **snapshot_fields((keep,)))
    with pytest.raises(ValueError, match="semantic session change"):
        PlanRevisionProposal(proposal_id="p", **snapshot_fields(()))


def test_proposal_is_immutable_and_requires_canonical_fingerprint():
    proposal = PlanRevisionProposal(proposal_id="p", **snapshot_fields((change(),)))
    with pytest.raises(FrozenInstanceError):
        proposal.source_plan_version = 4
    with pytest.raises(ValueError, match="sha256"):
        PlanRevisionProposal(proposal_id="p", **{**snapshot_fields((change(),)), "input_fingerprint": "abc"})


def evaluation(status, proposed_changes):
    fields = snapshot_fields(proposed_changes)
    fields["proposed_changes"] = fields.pop("changes")
    return PlanAdaptationEvaluation(adaptation_id="adaptation-1", status=status, **fields)


def test_evaluation_supports_consistent_no_change_and_change_snapshots():
    no_change = evaluation(AdaptationEvaluationStatus.NO_CHANGE, ())
    proposed = evaluation(AdaptationEvaluationStatus.CHANGE_PROPOSED, (change(),))
    assert no_change.proposed_changes == ()
    assert proposed.proposed_changes[0].session_id == "session-a"
    with pytest.raises(FrozenInstanceError):
        no_change.status = AdaptationEvaluationStatus.CHANGE_PROPOSED


def test_evaluation_rejects_status_change_inconsistency_and_invalid_source_version():
    with pytest.raises(ValueError, match="must not contain"):
        evaluation(AdaptationEvaluationStatus.NO_CHANGE, (change(),))
    with pytest.raises(ValueError, match="requires at least one"):
        evaluation(AdaptationEvaluationStatus.CHANGE_PROPOSED, ())
    fields = snapshot_fields(())
    fields["proposed_changes"] = fields.pop("changes")
    fields["source_plan_version"] = 0
    with pytest.raises(ValueError, match="int >= 1"):
        PlanAdaptationEvaluation(adaptation_id="a", status=AdaptationEvaluationStatus.NO_CHANGE, **fields)


def test_evaluation_normalizes_collection_order_deterministically():
    first = change(session_id="b", day=2)
    second = change(AdaptationAction.SKIP, session_id="a", day=1)
    assert evaluation(AdaptationEvaluationStatus.CHANGE_PROPOSED, (first, second)).proposed_changes == (second, first)


def test_reason_and_warning_code_order_is_canonical():
    reasons = (
        AdaptationReasonCode.STRESS_STACKING_RISK,
        AdaptationReasonCode.RECOVERY_PROTECTION,
    )
    warnings = (
        AdaptationWarningCode.SOURCE_EVIDENCE_INCOMPLETE,
        AdaptationWarningCode.CONTEXT_INCOMPLETE,
    )
    fields = snapshot_fields((change(),))
    fields.update(reason_codes=reasons, warning_codes=warnings)
    proposal = PlanRevisionProposal(proposal_id="p", **fields)
    assert proposal.reason_codes == tuple(sorted(reasons, key=lambda code: code.value))
    assert proposal.warning_codes == tuple(sorted(warnings, key=lambda code: code.value))


def test_logically_identical_snapshots_are_equal_regardless_of_input_order():
    first_reasons = (
        AdaptationReasonCode.STRESS_STACKING_RISK,
        AdaptationReasonCode.RECOVERY_PROTECTION,
    )
    second_reasons = tuple(reversed(first_reasons))
    first_warnings = (
        AdaptationWarningCode.SOURCE_EVIDENCE_INCOMPLETE,
        AdaptationWarningCode.CONTEXT_INCOMPLETE,
    )
    second_warnings = tuple(reversed(first_warnings))
    first_changes = (
        SessionAdaptationChange(
            "swim", D + timedelta(days=3), AdaptationAction.SHORTEN,
            first_reasons, target_duration_minutes=30,
        ),
        SessionAdaptationChange(
            "endurance", D + timedelta(days=3), AdaptationAction.SKIP,
            second_reasons,
        ),
    )
    second_changes = tuple(reversed((
        SessionAdaptationChange(
            "swim", D + timedelta(days=3), AdaptationAction.SHORTEN,
            second_reasons, target_duration_minutes=30,
        ),
        SessionAdaptationChange(
            "endurance", D + timedelta(days=3), AdaptationAction.SKIP,
            first_reasons,
        ),
    )))
    first_fields = snapshot_fields(first_changes)
    first_fields.update(reason_codes=first_reasons, warning_codes=first_warnings)
    second_fields = snapshot_fields(second_changes)
    second_fields.update(reason_codes=second_reasons, warning_codes=second_warnings)

    assert PlanRevisionProposal(proposal_id="p", **first_fields) == PlanRevisionProposal(
        proposal_id="p", **second_fields,
    )
