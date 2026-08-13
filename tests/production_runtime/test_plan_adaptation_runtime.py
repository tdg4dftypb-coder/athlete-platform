from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import duckdb
import pytest

from activity_reconciliation.models import ReconciliationResult
from morning_briefing.input_models import MorningBriefingInput, RecoveryBriefingInput, TrainingBriefingInput
from plan_adaptation.models import (
    AdaptationAction, AdaptationReasonCode, AdaptationWarningCode,
    SessionAdaptationChange,
)
from plan_adaptation.persistence import DuckDbPlanAdaptationRepository
from plan_adaptation.revision import PlanRevisionValidationCode, PlanRevisionValidationError
from plan_adaptation.runtime import ADAPTATION_CORRUPT, INSUFFICIENT_PLAN_HORIZON, PlanAdaptationRuntimeAdapter
from production_runtime.assessment_snapshot import AssessmentSnapshot, AssessmentSnapshotCodec
from production_runtime.coordinator import RuntimePhaseError
from production_runtime.models import PhaseStatus
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository


D = date(2026, 8, 13)
NOW = datetime(2026, 8, 13, 6, tzinfo=timezone.utc)


class Clock:
    def now_utc(self): return NOW


class Reconciliations:
    def __init__(self, value=None): self.value = value
    def get_latest_for_date(self, day):
        return self.value if self.value is not None and self.value.target_local_date == day else None


class Snapshots:
    def __init__(self, value): self.value = value
    def get_by_runtime_id(self, runtime_id): return self.value


def session(identifier, day, duration=60, priority=3, session_type="ENDURANCE"):
    return PlannedSession(identifier, day, PlannedSessionKind.TRAINING, session_type,
                          duration, 50.0, "MODERATE", priority, ("baseline",))


def plan(end_offset=9, extra=()):
    sessions = tuple(
        session(f"session-{offset}", D + timedelta(days=offset),
                session_type="RUNNING" if offset == 1 else "ENDURANCE")
        for offset in range(-7, end_offset + 1)
    ) + tuple(extra)
    return TrainingPlan("plan-a", D - timedelta(days=7), D + timedelta(days=end_offset), 1, NOW, sessions)


def snapshot(score=82, fatigue="LOW", runtime_id="runtime-1", target=D):
    value = MorningBriefingInput(
        generated_at=NOW,
        recovery=RecoveryBriefingInput(score, "READY", "summary", False, "normal", "normal", "good"),
        training=TrainingBriefingInput("Run", "60 min", 60, "MODERATE", True, "RUNNING", 300.0, fatigue),
        biomarkers=None,
    )
    return AssessmentSnapshot(runtime_id, target, NOW, value, AssessmentSnapshotCodec.artifact_id_for(value))


def reconciliation(fingerprint="a", target=D):
    return ReconciliationResult(
        f"reconciliation-{fingerprint}", "sha256:" + fingerprint * 64, "1.0", target,
        "Europe/Warsaw", "plan-a", 1, True, (), (), (), (), NOW,
    )


def context(day=D, runtime_id="runtime-1"):
    return SimpleNamespace(target_local_date=day, result=SimpleNamespace(runtime_id=runtime_id))


def adapter(tmp_path, score=82, source=None, reconciliation_value=None, fatigue="LOW"):
    plans = DuckDbTrainingPlanRepository(tmp_path / "plans.duckdb")
    plans.save(source or plan())
    audit = DuckDbPlanAdaptationRepository(tmp_path / "adaptation.duckdb")
    snapshots = Snapshots(snapshot(score, fatigue))
    runtime = PlanAdaptationRuntimeAdapter(
        plans, Reconciliations(reconciliation_value), snapshots, audit, Clock()
    )
    return runtime, context(), plans, audit, snapshots


def test_no_change_runtime_retry_persists_one_evaluation(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path)
    first = runtime.execute(ctx)
    second = runtime.execute(ctx)
    assert first.status is PhaseStatus.COMPLETED and not first.changed_state
    assert second.artifact_ids == first.artifact_ids
    assert len(audit.get_evaluation_history()) == 1
    assert plans.get_by_id("plan-a").version == 1


def test_applied_running_session_retry_does_not_create_vn_plus_2_or_change_today(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55)
    today_before = next(s for s in plans.get_by_id("plan-a").sessions if s.date == D)
    first = runtime.execute(ctx)
    second = runtime.execute(ctx)
    latest = plans.get_by_id("plan-a")
    target = next(s for s in latest.sessions if s.session_id == "session-1")
    assert first.changed_state and not second.changed_state
    assert latest.version == 2 and target.session_type == "RUNNING" and target.duration_minutes == 42
    assert next(s for s in latest.sessions if s.date == D) == today_before
    assert len(audit.get_evaluation_history()) == 1


def test_reconciliation_only_change_changes_context_not_policy_trigger_or_plan(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55, reconciliation_value=reconciliation("a"))
    first = runtime.execute(ctx)
    first_evaluation = audit.get_evaluation_by_id(first.artifact_ids[0])
    runtime.reconciliations.value = reconciliation("b")
    second = runtime.execute(ctx)
    rebuilt = runtime.context_builder.build(
        evaluation_date=D, source_plan=plans.get_by_id("plan-a"), historical_planned_sessions=tuple(
            s for s in plans.get_by_id("plan-a").sessions if D - timedelta(days=7) <= s.date <= D
        ), reconciliations=(runtime.reconciliations.value,), training_load=None,
        athlete_state=None, constraints=None, weekly_rhythm=None, built_at=NOW,
    )
    assert rebuilt.input_fingerprint != first_evaluation.input_fingerprint
    assert second.artifact_ids == first.artifact_ids
    assert plans.get_by_id("plan-a").version == 2
    assert len(audit.get_evaluation_history()) == 1


def test_same_day_new_policy_evidence_does_not_shorten_same_session_twice(tmp_path):
    runtime, ctx, plans, audit, snapshots = adapter(tmp_path, score=55)
    first = runtime.execute(ctx)
    snapshots.value = snapshot(82, "HIGH")
    second = runtime.execute(ctx)
    assert second.artifact_ids == first.artifact_ids
    assert plans.get_by_id("plan-a").version == 2
    assert next(s for s in plans.get_by_id("plan-a").sessions if s.session_id == "session-1").duration_minutes == 42
    assert len(audit.get_evaluation_history()) == 1


class DifferentSessionPolicy:
    policy_version = "1.0"
    def __init__(self, delegate): self.delegate = delegate
    def evaluate(self, adaptation_context, *, evaluated_at):
        original = self.delegate.evaluate(adaptation_context, evaluated_at=evaluated_at)
        target = next(s for s in adaptation_context.future_sessions if s.session_id == "session-2")
        return replace(
            original,
            adaptation_id="adaptation:1.0:" + adaptation_context.input_fingerprint + ":session-2",
            proposed_changes=(SessionAdaptationChange(
                target.session_id, target.date, AdaptationAction.SHORTEN,
                (AdaptationReasonCode.RECOVERY_PROTECTION,), target_duration_minutes=42,
            ),),
        )


def test_same_day_changed_trigger_can_adapt_a_different_session(tmp_path):
    runtime, ctx, plans, audit, snapshots = adapter(tmp_path, score=55)
    runtime.execute(ctx)
    snapshots.value = snapshot(82, "HIGH")
    runtime.policy = DifferentSessionPolicy(runtime.policy)
    second = runtime.execute(ctx)
    latest = plans.get_by_id("plan-a")
    assert second.changed_state and latest.version == 3
    assert next(s for s in latest.sessions if s.session_id == "session-1").duration_minutes == 42
    assert next(s for s in latest.sessions if s.session_id == "session-2").duration_minutes == 42
    assert len(audit.get_evaluation_history()) == 2


def test_next_day_new_evidence_can_adapt_a_different_session(tmp_path):
    runtime, ctx, plans, audit, snapshots = adapter(tmp_path, score=55)
    runtime.execute(ctx)
    snapshots.value = snapshot(82, "HIGH", runtime_id="runtime-2", target=D + timedelta(days=1))
    second = runtime.execute(context(D + timedelta(days=1), "runtime-2"))
    latest = plans.get_by_id("plan-a")
    assert second.changed_state and latest.version == 3
    assert next(s for s in latest.sessions if s.session_id == "session-1").duration_minutes == 42
    assert next(s for s in latest.sessions if s.session_id == "session-2").duration_minutes == 42
    assert len(audit.get_evaluation_history()) == 2


def test_insufficient_future_horizon_is_typed_skip_without_artifacts(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55, source=plan(end_offset=3))
    result = runtime.execute(ctx)
    assert result.status is PhaseStatus.SKIPPED and not result.changed_state
    assert result.warning_codes == (INSUFFICIENT_PLAN_HORIZON,)
    assert audit.get_evaluation_history() == () and plans.get_by_id("plan-a").version == 1


class InterruptRevision:
    def apply(self, *args, **kwargs): raise KeyboardInterrupt()


def test_partial_evaluation_and_proposal_resume_without_policy_recompute(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55)
    runtime.revision_service = InterruptRevision()
    with pytest.raises(KeyboardInterrupt): runtime.execute(ctx)
    entry = audit.get_history_entry(audit.get_evaluation_history()[0].adaptation_id)
    assert entry.proposal is not None and entry.revision is None
    runtime.revision_service = None
    from plan_adaptation.revision import TrainingPlanRevisionService
    runtime.revision_service = TrainingPlanRevisionService()
    result = runtime.execute(ctx)
    assert result.changed_state and plans.get_by_id("plan-a").version == 2
    assert len(audit.get_evaluation_history()) == 1


class InterruptAfterPlanWrite:
    def __init__(self, delegate): self.delegate = delegate
    def persist_applied(self, evaluation, proposal, revised, record):
        self.delegate.audit.save_evaluation(evaluation)
        self.delegate.audit.save_proposal(evaluation.adaptation_id, proposal)
        self.delegate.plans.append_revision(proposal.source_plan_version, revised)
        raise KeyboardInterrupt()


def test_plan_written_before_applied_resume_finishes_same_revision(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55)
    original = runtime.persistence
    runtime.persistence = InterruptAfterPlanWrite(original)
    with pytest.raises(KeyboardInterrupt): runtime.execute(ctx)
    assert plans.get_by_id("plan-a").version == 2
    runtime.persistence = original
    result = runtime.execute(ctx)
    assert not result.changed_state and plans.get_by_id("plan-a").version == 2
    assert audit.get_history_entry(result.artifact_ids[0]).revision is not None


def test_unresolvable_applied_is_corruption(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55)
    runtime.execute(ctx)
    connection = duckdb.connect(str(tmp_path / "plans.duckdb"))
    connection.execute("DELETE FROM training_plan_revisions")
    connection.close()
    with pytest.raises(RuntimePhaseError) as captured: runtime.execute(ctx)
    assert captured.value.code == ADAPTATION_CORRUPT


def test_competing_plan_revision_conflict_is_runtime_failure_not_rejected(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55)
    runtime.revision_service = InterruptRevision()
    with pytest.raises(KeyboardInterrupt): runtime.execute(ctx)
    source = plans.get_by_id("plan-a")
    competing = replace(source, version=2, generated_at=NOW + timedelta(minutes=1),
                        sessions=tuple(replace(s, intensity="HIGH") if s.session_id == "session-2" else s for s in source.sessions))
    plans.append_revision(1, competing)
    from plan_adaptation.revision import TrainingPlanRevisionService
    runtime.revision_service = TrainingPlanRevisionService()
    with pytest.raises(RuntimePhaseError) as captured: runtime.execute(ctx)
    assert captured.value.code == ADAPTATION_CORRUPT
    assert audit.get_history_entry(audit.get_evaluation_history()[0].adaptation_id).revision is None


class RejectingRevision:
    def apply(self, *args, **kwargs):
        raise PlanRevisionValidationError(PlanRevisionValidationCode.STALE_SOURCE_VERSION, "stale")


def test_typed_validation_failure_persists_rejected_without_result_plan(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55)
    runtime.revision_service = RejectingRevision()
    result = runtime.execute(ctx)
    entry = audit.get_history_entry(result.artifact_ids[0])
    assert result.status is PhaseStatus.COMPLETED and not result.changed_state
    assert entry.revision.status.value == "REJECTED"
    assert entry.revision.result_plan_id is None and plans.get_by_id("plan-a").version == 1


class UnexpectedPersistenceFailure:
    def persist_applied(self, *args, **kwargs): raise RuntimeError("storage unavailable")


def test_unexpected_persistence_failure_is_not_normal_rejected(tmp_path):
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55)
    runtime.persistence = UnexpectedPersistenceFailure()
    with pytest.raises(RuntimeError, match="storage unavailable"):
        runtime.execute(ctx)
    entry = audit.get_history_entry(audit.get_evaluation_history()[0].adaptation_id)
    assert entry.proposal is not None and entry.revision is None
    assert plans.get_by_id("plan-a").version == 1


def test_same_day_multi_session_equal_priority_is_safe_no_change(tmp_path):
    extra = (session("session-1b", D + timedelta(days=1), priority=3, session_type="SWIM"),)
    runtime, ctx, plans, audit, _ = adapter(tmp_path, score=55, source=plan(extra=extra))
    result = runtime.execute(ctx)
    evaluation = audit.get_evaluation_by_id(result.artifact_ids[0])
    assert not result.changed_state and plans.get_by_id("plan-a").version == 1
    assert AdaptationWarningCode.AMBIGUOUS_ADAPTATION_TARGET in evaluation.warning_codes
