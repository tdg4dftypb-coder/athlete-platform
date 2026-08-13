"""Stage 29.4 proposal construction, validation, and in-memory plan revision."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json

from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.reduction import (
    reduced_duration_minutes_v1,
    reduced_target_tss_v1,
)

from plan_adaptation.models import (
    AdaptationAction,
    AdaptationEvaluationStatus,
    PlanAdaptationEvaluation,
    PlanRevisionProposal,
    SessionAdaptationChange,
)


class PlanRevisionValidationCode(Enum):
    WRONG_SOURCE_PLAN = "wrong_source_plan"
    STALE_SOURCE_VERSION = "stale_source_version"
    SOURCE_VERSION_MISMATCH = "source_version_mismatch"
    UNKNOWN_SESSION = "unknown_session"
    SESSION_DATE_MISMATCH = "session_date_mismatch"
    SESSION_OUTSIDE_MUTATION_WINDOW = "session_outside_mutation_window"
    ILLEGAL_ACTION_FOR_SOURCE = "illegal_action_for_source"
    NOT_SEMANTIC_REDUCTION = "not_semantic_reduction"
    UNSUPPORTED_MATERIALIZATION = "unsupported_materialization"
    NO_SEMANTIC_CHANGE = "no_semantic_change"


class PlanRevisionValidationError(ValueError):
    def __init__(self, code: PlanRevisionValidationCode, message: str) -> None:
        self.code = code
        super().__init__(message)


class PlanRevisionProposalBuilder:
    """Converts a policy evaluation to an immutable proposal without I/O."""

    def build(self, evaluation: PlanAdaptationEvaluation) -> PlanRevisionProposal | None:
        if not isinstance(evaluation, PlanAdaptationEvaluation):
            raise TypeError("evaluation must be PlanAdaptationEvaluation")
        if evaluation.status is AdaptationEvaluationStatus.NO_CHANGE:
            return None

        payload = {
            "policy_version": evaluation.policy_version,
            "evaluation_date": evaluation.evaluation_date.isoformat(),
            "source_plan_id": evaluation.source_plan_id,
            "source_plan_version": evaluation.source_plan_version,
            "context_window": (
                evaluation.context_window.context_start.isoformat(),
                evaluation.context_window.context_end.isoformat(),
            ),
            "mutation_window": (
                evaluation.mutation_window.mutation_start.isoformat(),
                evaluation.mutation_window.mutation_end.isoformat(),
            ),
            "changes": [self._change_payload(change) for change in evaluation.proposed_changes],
            "reason_codes": [code.value for code in evaluation.reason_codes],
            "warning_codes": [code.value for code in evaluation.warning_codes],
            "input_fingerprint": evaluation.input_fingerprint,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return PlanRevisionProposal(
            proposal_id=f"proposal:sha256:{digest}",
            policy_version=evaluation.policy_version,
            evaluation_date=evaluation.evaluation_date,
            source_plan_id=evaluation.source_plan_id,
            source_plan_version=evaluation.source_plan_version,
            context_window=evaluation.context_window,
            mutation_window=evaluation.mutation_window,
            changes=evaluation.proposed_changes,
            reason_codes=evaluation.reason_codes,
            warning_codes=evaluation.warning_codes,
            input_fingerprint=evaluation.input_fingerprint,
            evaluated_at=evaluation.evaluated_at,
        )

    @staticmethod
    def _change_payload(change: SessionAdaptationChange) -> dict[str, object]:
        return {
            "session_id": change.session_id,
            "session_date": change.session_date.isoformat(),
            "action": change.action.value,
            "reason_codes": [code.value for code in change.reason_codes],
            "target_duration_minutes": change.target_duration_minutes,
            "target_intensity": change.target_intensity,
            "target_session_type": change.target_session_type,
        }


class PlanRevisionValidator:
    """Validates an entire proposal against exactly one immutable source plan."""

    def validate(self, proposal: PlanRevisionProposal, source_plan: TrainingPlan) -> None:
        if not isinstance(proposal, PlanRevisionProposal):
            raise TypeError("proposal must be PlanRevisionProposal")
        if not isinstance(source_plan, TrainingPlan):
            raise TypeError("source_plan must be TrainingPlan")
        if proposal.source_plan_id != source_plan.plan_id:
            self._reject(PlanRevisionValidationCode.WRONG_SOURCE_PLAN, "proposal targets a different plan_id")
        if proposal.source_plan_version < source_plan.version:
            self._reject(PlanRevisionValidationCode.STALE_SOURCE_VERSION, "proposal source version is stale")
        if proposal.source_plan_version > source_plan.version:
            self._reject(PlanRevisionValidationCode.SOURCE_VERSION_MISMATCH, "proposal source version is newer than plan")

        sessions_by_id = {session.session_id: session for session in source_plan.sessions}
        semantic_change_count = 0
        for change in proposal.changes:
            source = sessions_by_id.get(change.session_id)
            if source is None:
                self._reject(PlanRevisionValidationCode.UNKNOWN_SESSION, f"unknown session_id: {change.session_id}")
            if source.date != change.session_date:
                self._reject(PlanRevisionValidationCode.SESSION_DATE_MISMATCH, f"date mismatch for {change.session_id}")
            if not (proposal.mutation_window.mutation_start <= source.date <= proposal.mutation_window.mutation_end):
                self._reject(
                    PlanRevisionValidationCode.SESSION_OUTSIDE_MUTATION_WINDOW,
                    f"session {change.session_id} lies outside mutation window",
                )
            if change.action is AdaptationAction.KEEP:
                continue
            semantic_change_count += 1
            if change.action is AdaptationAction.SHORTEN:
                self._validate_shorten(change, source)
            else:
                self._reject(
                    PlanRevisionValidationCode.UNSUPPORTED_MATERIALIZATION,
                    f"{change.action.value} has no canonical Stage 29.4 materialization",
                )
        if semantic_change_count == 0:
            self._reject(PlanRevisionValidationCode.NO_SEMANTIC_CHANGE, "proposal has no materialized semantic change")

    def _validate_shorten(self, change: SessionAdaptationChange, source: PlannedSession) -> None:
        if source.kind is not PlannedSessionKind.TRAINING:
            self._reject(PlanRevisionValidationCode.ILLEGAL_ACTION_FOR_SOURCE, "SHORTEN requires TRAINING source")
        target = change.target_duration_minutes
        if target is None or target <= 0 or target >= source.duration_minutes:
            self._reject(PlanRevisionValidationCode.NOT_SEMANTIC_REDUCTION, "SHORTEN target must satisfy 0 < target < source")
        canonical_target = reduced_duration_minutes_v1(source.duration_minutes)
        if canonical_target >= source.duration_minutes or target != canonical_target:
            self._reject(
                PlanRevisionValidationCode.UNSUPPORTED_MATERIALIZATION,
                "SHORTEN target must match canonical v1 duration reduction",
            )

    @staticmethod
    def _reject(code: PlanRevisionValidationCode, message: str) -> None:
        raise PlanRevisionValidationError(code, message)


class TrainingPlanRevisionService:
    """Atomically validates and materializes an in-memory TrainingPlan N+1."""

    def __init__(self, validator: PlanRevisionValidator | None = None) -> None:
        self._validator = validator or PlanRevisionValidator()

    def apply(
        self,
        proposal: PlanRevisionProposal,
        source_plan: TrainingPlan,
        *,
        generated_at: datetime,
    ) -> TrainingPlan:
        if not isinstance(generated_at, datetime):
            raise TypeError("generated_at must be datetime")
        self._validator.validate(proposal, source_plan)

        changes = {
            change.session_id: change
            for change in proposal.changes
            if change.action is not AdaptationAction.KEEP
        }
        revised_sessions = tuple(
            self._materialize(session, changes.get(session.session_id))
            for session in source_plan.sessions
        )
        if revised_sessions == source_plan.sessions:
            raise PlanRevisionValidationError(
                PlanRevisionValidationCode.NO_SEMANTIC_CHANGE,
                "candidate sessions are semantically identical to source",
            )
        return TrainingPlan(
            plan_id=source_plan.plan_id,
            start_date=source_plan.start_date,
            end_date=source_plan.end_date,
            version=source_plan.version + 1,
            generated_at=generated_at,
            sessions=revised_sessions,
            supersedes_plan_id=source_plan.supersedes_plan_id,
        )

    @staticmethod
    def _materialize(
        source: PlannedSession,
        change: SessionAdaptationChange | None,
    ) -> PlannedSession:
        if change is None:
            return source
        if change.action is AdaptationAction.SHORTEN:
            return replace(
                source,
                duration_minutes=change.target_duration_minutes,
                target_tss=reduced_target_tss_v1(source.target_tss),
            )
        return source
