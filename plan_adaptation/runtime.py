"""Production-runtime orchestration for the existing adaptation domain services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from hashlib import sha256
import json

from application.athlete_assessment import (
    AthleteAssessment, AthleteAssessmentReason, AthleteAssessmentStatus, FatigueStatus,
)
from application.training_assessment import TrainingAssessment, TrainingAssessmentStatus
from plan_adaptation.builder import AdaptationContextBuildError, AdaptationContextBuilder
from plan_adaptation.context import AdaptationTrainingLoad
from plan_adaptation.models import AdaptationEvaluationStatus
from plan_adaptation.persistence import (
    AdaptationHistoryReader, AdaptationPersistenceConflictError,
    AdaptationPersistenceCoordinator, PlanRevisionRecord, PlanRevisionStatus,
)
from plan_adaptation.policy import DeterministicAdaptationPolicy
from plan_adaptation.revision import (
    PlanRevisionProposalBuilder, PlanRevisionValidationError, TrainingPlanRevisionService,
)
from production_runtime.coordinator import RuntimePhaseError, RuntimePhaseOutcome
from production_runtime.models import PhaseStatus, RuntimeWarning


INSUFFICIENT_PLAN_HORIZON = "adaptation_insufficient_plan_horizon"
ADAPTATION_REJECTED = "adaptation_rejected"
ADAPTATION_CORRUPT = "adaptation_corrupt"


def assessment_from_snapshot(snapshot) -> AthleteAssessment | None:
    """Project only canonical assessment snapshot fields used by policy v1."""
    value = snapshot.input
    recovery = value.recovery
    training = value.training
    if recovery is None and training is None:
        return None
    reasons = []
    if recovery is not None and recovery.score is not None and recovery.score < 70:
        reasons.append(AthleteAssessmentReason.LOW_RECOVERY)
    fatigue = FatigueStatus.HIGH if training and str(training.fatigue_status).lower() == "high" else FatigueStatus.NORMAL
    if fatigue is FatigueStatus.HIGH:
        reasons.append(AthleteAssessmentReason.HIGH_FATIGUE)
    training_assessment = TrainingAssessment(
        as_of=value.generated_at,
        period=None,
        status=(TrainingAssessmentStatus.NO_CLEAR_PATTERN if training is not None
                else TrainingAssessmentStatus.NO_TRAINING_DATA),
        supporting_patterns=(),
    )
    return AthleteAssessment(
        as_of=value.generated_at,
        status=AthleteAssessmentStatus.CAUTION if reasons else AthleteAssessmentStatus.STABLE,
        training_assessment=training_assessment,
        reasons=tuple(reasons),
        fatigue_status=fatigue,
    )


@dataclass
class PlanAdaptationRuntimeAdapter:
    """Retry-safe bridge from a daily runtime attempt to Stage 29 artifacts."""

    plans: object
    reconciliations: object
    snapshots: object
    audit: object
    clock: object
    context_builder: object = None
    policy: object = None
    proposal_builder: object = None
    revision_service: object = None
    persistence: object = None
    history: object = None

    def __post_init__(self):
        self.context_builder = self.context_builder or AdaptationContextBuilder()
        self.policy = self.policy or DeterministicAdaptationPolicy()
        self.proposal_builder = self.proposal_builder or PlanRevisionProposalBuilder()
        self.revision_service = self.revision_service or TrainingPlanRevisionService()
        self.persistence = self.persistence or AdaptationPersistenceCoordinator(self.audit, self.plans)
        self.history = self.history or AdaptationHistoryReader(self.audit, self.plans)

    def execute(self, runtime_context):
        day = runtime_context.target_local_date
        plan = self.plans.get_for_date(day)
        if plan is None:
            raise RuntimePhaseError("missing_training_plan")
        snapshot = self.snapshots.get_by_runtime_id(runtime_context.result.runtime_id)
        if snapshot is None:
            raise RuntimePhaseError("assessment_snapshot_missing")
        athlete_state = assessment_from_snapshot(snapshot)
        external_key = self._policy_trigger_key(day, self.policy.policy_version, athlete_state)
        prior = self.audit.get_runtime_guard(external_key)
        if prior is not None:
            return self._resume(prior, plan)
        historical = tuple(
            session for session in plan.sessions
            if day - timedelta(days=7) <= session.date <= day
        )
        reconciliation_values = tuple(
            item for offset in range(8)
            if (item := self.reconciliations.get_latest_for_date(day - timedelta(days=offset))) is not None
        )
        training = snapshot.input.training
        load = None
        if training is not None and training.recent_training_load is not None:
            load = AdaptationTrainingLoad(recent_training_load_7d=training.recent_training_load)
        try:
            context = self.context_builder.build(
                evaluation_date=day, source_plan=plan,
                historical_planned_sessions=historical,
                reconciliations=reconciliation_values,
                training_load=load, athlete_state=athlete_state,
                constraints=None, weekly_rhythm=None, built_at=self.clock.now_utc(),
            )
        except AdaptationContextBuildError:
            return RuntimePhaseOutcome(
                status=PhaseStatus.SKIPPED, warning_codes=(INSUFFICIENT_PLAN_HORIZON,),
                warnings=(RuntimeWarning(INSUFFICIENT_PLAN_HORIZON, source="plan_adaptation"),),
            )

        # A self-produced plan revision is not new evidence. Reuse a same-day
        # completed evaluation when its external snapshot/reconciliation digest matches.
        evaluation = self.policy.evaluate(context, evaluated_at=self.clock.now_utc())
        prior_session_entry = self._prior_applied_target(evaluation)
        if prior_session_entry is not None:
            return self._outcome_for_entry(prior_session_entry)
        self.audit.save_evaluation(evaluation)
        self.audit.save_runtime_guard(external_key, evaluation.adaptation_id)
        if evaluation.status is AdaptationEvaluationStatus.NO_CHANGE:
            return RuntimePhaseOutcome(artifact_ids=(evaluation.adaptation_id,))

        proposal = self.proposal_builder.build(evaluation)
        self.audit.save_proposal(evaluation.adaptation_id, proposal)
        try:
            revised = self.revision_service.apply(proposal, plan, generated_at=self.clock.now_utc())
        except PlanRevisionValidationError as error:
            record = PlanRevisionRecord.rejected(proposal, evaluation.adaptation_id, error.code, self.clock.now_utc())
            self.persistence.persist_rejected(evaluation, proposal, record)
            return RuntimePhaseOutcome(
                artifact_ids=(evaluation.adaptation_id, proposal.proposal_id, record.revision_id),
                warning_codes=(ADAPTATION_REJECTED,),
                warnings=(RuntimeWarning(ADAPTATION_REJECTED, error.code.value, "plan_adaptation"),),
            )
        record = PlanRevisionRecord.applied(proposal, evaluation.adaptation_id, revised, self.clock.now_utc())
        try:
            self.persistence.persist_applied(evaluation, proposal, revised, record)
        except AdaptationPersistenceConflictError as error:
            raise RuntimePhaseError("adaptation_persistence_conflict", str(error)) from error
        return RuntimePhaseOutcome(
            changed_state=True, training_plan_id=revised.plan_id,
            artifact_ids=(evaluation.adaptation_id, proposal.proposal_id, record.revision_id, revised.plan_id),
        )

    def _resume(self, adaptation_id, current_plan):
        applied_now = False
        try:
            entry = self.history.get_entry(adaptation_id)
        except Exception as error:
            raise RuntimePhaseError(ADAPTATION_CORRUPT, str(error)) from error
        if entry is None:
            raise RuntimePhaseError(ADAPTATION_CORRUPT, "runtime guard evaluation is missing")
        if entry.evaluation.status is AdaptationEvaluationStatus.NO_CHANGE:
            return RuntimePhaseOutcome(artifact_ids=(entry.evaluation.adaptation_id,))
        if entry.proposal is None:
            proposal = self.proposal_builder.build(entry.evaluation)
            if proposal is None:
                raise RuntimePhaseError(ADAPTATION_CORRUPT, "change evaluation has no proposal")
            self.audit.save_proposal(adaptation_id, proposal)
            entry = self.history.get_entry(adaptation_id)
        if entry.revision is None:
            source = self.plans.get_by_id_version(entry.proposal.source_plan_id, entry.proposal.source_plan_version)
            if source is None:
                raise RuntimePhaseError(ADAPTATION_CORRUPT, "proposal source plan is missing")
            revised = self.revision_service.apply(entry.proposal, source, generated_at=self.clock.now_utc())
            persisted = self.plans.get_by_id_version(revised.plan_id, revised.version)
            record = PlanRevisionRecord.applied(entry.proposal, adaptation_id, revised, self.clock.now_utc())
            if persisted is None:
                self.persistence.persist_applied(entry.evaluation, entry.proposal, revised, record)
                applied_now = True
            elif persisted.sessions == revised.sessions and persisted.start_date == revised.start_date and persisted.end_date == revised.end_date:
                record = PlanRevisionRecord.applied(entry.proposal, adaptation_id, persisted, self.clock.now_utc())
                self.audit.save_revision(record)
            else:
                raise RuntimePhaseError(ADAPTATION_CORRUPT, "result plan payload mismatch")
            entry = self.history.get_entry(adaptation_id)
        record = entry.revision
        return self._outcome_for_entry(entry, changed_state=applied_now)

    def _outcome_for_entry(self, entry, *, changed_state=False):
        if entry.evaluation.status is AdaptationEvaluationStatus.NO_CHANGE:
            return RuntimePhaseOutcome(artifact_ids=(entry.evaluation.adaptation_id,))
        record = entry.revision
        artifacts = (entry.evaluation.adaptation_id, entry.proposal.proposal_id, record.revision_id)
        if record.status is PlanRevisionStatus.REJECTED:
            return RuntimePhaseOutcome(artifact_ids=artifacts, warning_codes=(ADAPTATION_REJECTED,))
        if self.plans.get_by_id_version(record.result_plan_id, record.result_plan_version) is None:
            raise RuntimePhaseError(ADAPTATION_CORRUPT, "APPLIED result is unresolvable")
        return RuntimePhaseOutcome(
            changed_state=changed_state, training_plan_id=record.result_plan_id,
            artifact_ids=artifacts + (record.result_plan_id,),
        )

    def _prior_applied_target(self, evaluation):
        for change in evaluation.proposed_changes:
            entry = self.audit.get_applied_for_session(
                evaluation.evaluation_date, evaluation.policy_version,
                change.session_id, change.action,
            )
            if entry is not None:
                return entry
        return None

    @staticmethod
    def _policy_trigger_key(day, policy_version, assessment):
        payload = {
            "evaluation_date": day.isoformat(),
            "policy_version": policy_version,
            "assessment": None if assessment is None else {
                "status": assessment.status.value,
                "fatigue_status": assessment.fatigue_status.value,
                "reasons": sorted(reason.value for reason in assessment.reasons if reason in (
                    AthleteAssessmentReason.LOW_RECOVERY,
                    AthleteAssessmentReason.HIGH_FATIGUE,
                )),
            },
        }
        return "adaptation-trigger:sha256:" + sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
