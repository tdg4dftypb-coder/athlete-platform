"""Immutable domain contract for deterministic future-plan adaptation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum


class AdaptationAction(Enum):
    KEEP = "KEEP"
    SHORTEN = "SHORTEN"
    REDUCE_INTENSITY = "REDUCE_INTENSITY"
    DOWNGRADE = "DOWNGRADE"
    SKIP = "SKIP"


class AdaptationReasonCode(Enum):
    RECOVERY_PROTECTION = "recovery_protection"
    HIGH_RECENT_TRAINING_LOAD = "high_recent_training_load"
    STRESS_STACKING_RISK = "stress_stacking_risk"
    UNPLANNED_ACTIVITY_LOAD = "unplanned_activity_load"
    REPLACEMENT_ACTIVITY_LOAD = "replacement_activity_load"
    PARTIAL_SESSION_EVIDENCE = "partial_session_evidence"
    SKIPPED_SESSION_NO_MAKEUP = "skipped_session_no_makeup"
    PROTECTED_RECOVERY_DAY = "protected_recovery_day"
    MULTI_SESSION_LOAD = "multi_session_load"


class AdaptationWarningCode(Enum):
    CONTEXT_INCOMPLETE = "context_incomplete"
    SOURCE_EVIDENCE_INCOMPLETE = "source_evidence_incomplete"
    RECONCILIATION_UNAVAILABLE = "reconciliation_unavailable"
    RECONCILIATION_AMBIGUOUS = "reconciliation_ambiguous"
    RECONCILIATION_INCOMPLETE = "reconciliation_incomplete"
    ATHLETE_ASSESSMENT_UNAVAILABLE = "athlete_assessment_unavailable"
    TRAINING_LOAD_UNAVAILABLE = "training_load_unavailable"
    TRAINING_LOAD_PARTIAL = "training_load_partial"
    WEEKLY_RHYTHM_UNAVAILABLE = "weekly_rhythm_unavailable"
    ATHLETE_CONSTRAINTS_UNAVAILABLE = "athlete_constraints_unavailable"
    AMBIGUOUS_ADAPTATION_TARGET = "ambiguous_adaptation_target"


class AdaptationEvaluationStatus(Enum):
    NO_CHANGE = "NO_CHANGE"
    CHANGE_PROPOSED = "CHANGE_PROPOSED"


def _require_date(name: str, value: date) -> None:
    if type(value) is not date:
        raise TypeError(f"{name} must be a date instance (not datetime)")


def _require_non_empty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_codes(name: str, values: tuple, code_type: type[Enum]) -> tuple:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be tuple")
    if any(not isinstance(value, code_type) for value in values):
        raise TypeError(f"{name} must contain only {code_type.__name__}")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must not contain duplicates")
    return tuple(sorted(values, key=lambda value: value.value))


def _validate_fingerprint(value: str) -> None:
    _require_non_empty("input_fingerprint", value)
    prefix, separator, digest = value.partition(":")
    if prefix != "sha256" or separator != ":" or len(digest) != 64:
        raise ValueError("input_fingerprint must use sha256:<64 lowercase hex characters>")
    if any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("input_fingerprint must use sha256:<64 lowercase hex characters>")


@dataclass(frozen=True)
class AdaptationWindow:
    evaluation_date: date
    mutation_start: date
    mutation_end: date

    def __post_init__(self) -> None:
        for name in ("evaluation_date", "mutation_start", "mutation_end"):
            _require_date(name, getattr(self, name))
        if self.mutation_start <= self.evaluation_date:
            raise ValueError("mutation_start must be after evaluation_date")
        if self.mutation_end < self.mutation_start:
            raise ValueError("mutation_end must be on or after mutation_start")
        if self.mutation_end > self.evaluation_date + timedelta(days=7):
            raise ValueError("mutation window must not exceed the D+7 horizon")
        if self.mutation_start != self.evaluation_date + timedelta(days=1):
            raise ValueError("mutation_start must equal D+1")
        if self.mutation_end != self.evaluation_date + timedelta(days=7):
            raise ValueError("mutation_end must equal D+7")

    @classmethod
    def canonical(cls, evaluation_date: date) -> "AdaptationWindow":
        _require_date("evaluation_date", evaluation_date)
        return cls(evaluation_date, evaluation_date + timedelta(days=1), evaluation_date + timedelta(days=7))


@dataclass(frozen=True)
class AdaptationContextWindow:
    evaluation_date: date
    context_start: date
    context_end: date

    def __post_init__(self) -> None:
        for name in ("evaluation_date", "context_start", "context_end"):
            _require_date(name, getattr(self, name))
        if self.context_start > self.context_end:
            raise ValueError("context_start must be on or before context_end")
        if self.context_end != self.evaluation_date:
            raise ValueError("context_end must equal evaluation_date")
        if self.context_start < self.evaluation_date - timedelta(days=7):
            raise ValueError("context window must not begin before D-7")
        if self.context_start != self.evaluation_date - timedelta(days=7):
            raise ValueError("context_start must equal D-7")

    @classmethod
    def canonical(cls, evaluation_date: date) -> "AdaptationContextWindow":
        _require_date("evaluation_date", evaluation_date)
        return cls(evaluation_date, evaluation_date - timedelta(days=7), evaluation_date)


@dataclass(frozen=True)
class SessionAdaptationChange:
    session_id: str
    session_date: date
    action: AdaptationAction
    reason_codes: tuple[AdaptationReasonCode, ...]
    target_duration_minutes: int | None = None
    target_intensity: str | None = None
    target_session_type: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("session_id", self.session_id)
        _require_date("session_date", self.session_date)
        if not isinstance(self.action, AdaptationAction):
            raise TypeError("action must be AdaptationAction")
        canonical_reasons = _validate_codes("reason_codes", self.reason_codes, AdaptationReasonCode)
        object.__setattr__(self, "reason_codes", canonical_reasons)

        targets = (self.target_duration_minutes, self.target_intensity, self.target_session_type)
        if self.action in (AdaptationAction.KEEP, AdaptationAction.SKIP) and any(value is not None for value in targets):
            raise ValueError(f"{self.action.value} must not carry target mutation fields")
        if self.action is AdaptationAction.SHORTEN:
            if (
                not isinstance(self.target_duration_minutes, int)
                or isinstance(self.target_duration_minutes, bool)
                or self.target_duration_minutes <= 0
            ):
                raise ValueError("SHORTEN requires target_duration_minutes > 0")
            if self.target_intensity is not None or self.target_session_type is not None:
                raise ValueError("SHORTEN accepts only target_duration_minutes")
        if self.action is AdaptationAction.REDUCE_INTENSITY:
            if not isinstance(self.target_intensity, str) or not self.target_intensity.strip():
                raise ValueError("REDUCE_INTENSITY requires target_intensity")
            if self.target_duration_minutes is not None or self.target_session_type is not None:
                raise ValueError("REDUCE_INTENSITY accepts only target_intensity")
            object.__setattr__(self, "target_intensity", self.target_intensity.strip().upper())
        if self.action is AdaptationAction.DOWNGRADE:
            if not isinstance(self.target_session_type, str) or not self.target_session_type.strip():
                raise ValueError("DOWNGRADE requires target_session_type")
            if self.target_duration_minutes is not None or self.target_intensity is not None:
                raise ValueError("DOWNGRADE accepts only target_session_type")
            object.__setattr__(self, "target_session_type", self.target_session_type.strip().upper())


def _validate_snapshot(
    policy_version: str,
    evaluation_date: date,
    source_plan_id: str,
    source_plan_version: int,
    context_window: AdaptationContextWindow,
    mutation_window: AdaptationWindow,
    changes: tuple[SessionAdaptationChange, ...],
    reason_codes: tuple[AdaptationReasonCode, ...],
    warning_codes: tuple[AdaptationWarningCode, ...],
    input_fingerprint: str,
    evaluated_at: datetime,
) -> tuple[SessionAdaptationChange, ...]:
    _require_non_empty("policy_version", policy_version)
    _require_date("evaluation_date", evaluation_date)
    _require_non_empty("source_plan_id", source_plan_id)
    if not isinstance(source_plan_version, int) or isinstance(source_plan_version, bool) or source_plan_version < 1:
        raise ValueError("source_plan_version must be int >= 1")
    if not isinstance(context_window, AdaptationContextWindow):
        raise TypeError("context_window must be AdaptationContextWindow")
    if not isinstance(mutation_window, AdaptationWindow):
        raise TypeError("mutation_window must be AdaptationWindow")
    if context_window.evaluation_date != evaluation_date or mutation_window.evaluation_date != evaluation_date:
        raise ValueError("window evaluation dates must match evaluation_date")
    if not isinstance(changes, tuple):
        raise TypeError("changes must be tuple")
    if any(not isinstance(change, SessionAdaptationChange) for change in changes):
        raise TypeError("changes must contain only SessionAdaptationChange")
    canonical = tuple(sorted(changes, key=lambda change: (change.session_date, change.session_id)))
    identifiers = tuple(change.session_id for change in canonical)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate session_id changes are not allowed")
    if any(not (mutation_window.mutation_start <= change.session_date <= mutation_window.mutation_end) for change in canonical):
        raise ValueError("every change must be inside the mutation window")
    _validate_codes("reason_codes", reason_codes, AdaptationReasonCode)
    _validate_codes("warning_codes", warning_codes, AdaptationWarningCode)
    _validate_fingerprint(input_fingerprint)
    if not isinstance(evaluated_at, datetime):
        raise TypeError("evaluated_at must be datetime")
    return canonical


@dataclass(frozen=True)
class PlanRevisionProposal:
    proposal_id: str
    policy_version: str
    evaluation_date: date
    source_plan_id: str
    source_plan_version: int
    context_window: AdaptationContextWindow
    mutation_window: AdaptationWindow
    changes: tuple[SessionAdaptationChange, ...]
    reason_codes: tuple[AdaptationReasonCode, ...]
    warning_codes: tuple[AdaptationWarningCode, ...]
    input_fingerprint: str
    evaluated_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty("proposal_id", self.proposal_id)
        canonical = _validate_snapshot(
            self.policy_version, self.evaluation_date, self.source_plan_id,
            self.source_plan_version, self.context_window, self.mutation_window,
            self.changes, self.reason_codes, self.warning_codes,
            self.input_fingerprint, self.evaluated_at,
        )
        if not any(change.action is not AdaptationAction.KEEP for change in canonical):
            raise ValueError("proposal requires at least one semantic session change")
        object.__setattr__(self, "changes", canonical)
        object.__setattr__(self, "reason_codes", _validate_codes("reason_codes", self.reason_codes, AdaptationReasonCode))
        object.__setattr__(self, "warning_codes", _validate_codes("warning_codes", self.warning_codes, AdaptationWarningCode))


@dataclass(frozen=True)
class PlanAdaptationEvaluation:
    adaptation_id: str
    policy_version: str
    status: AdaptationEvaluationStatus
    evaluation_date: date
    context_window: AdaptationContextWindow
    mutation_window: AdaptationWindow
    source_plan_id: str
    source_plan_version: int
    proposed_changes: tuple[SessionAdaptationChange, ...]
    reason_codes: tuple[AdaptationReasonCode, ...]
    warning_codes: tuple[AdaptationWarningCode, ...]
    input_fingerprint: str
    evaluated_at: datetime

    def __post_init__(self) -> None:
        _require_non_empty("adaptation_id", self.adaptation_id)
        if not isinstance(self.status, AdaptationEvaluationStatus):
            raise TypeError("status must be AdaptationEvaluationStatus")
        canonical = _validate_snapshot(
            self.policy_version, self.evaluation_date, self.source_plan_id,
            self.source_plan_version, self.context_window, self.mutation_window,
            self.proposed_changes, self.reason_codes, self.warning_codes,
            self.input_fingerprint, self.evaluated_at,
        )
        has_semantic_change = any(change.action is not AdaptationAction.KEEP for change in canonical)
        if self.status is AdaptationEvaluationStatus.NO_CHANGE and canonical:
            raise ValueError("NO_CHANGE evaluation must not contain proposed_changes")
        if self.status is AdaptationEvaluationStatus.CHANGE_PROPOSED and not has_semantic_change:
            raise ValueError("CHANGE_PROPOSED requires at least one semantic session change")
        object.__setattr__(self, "proposed_changes", canonical)
        object.__setattr__(self, "reason_codes", _validate_codes("reason_codes", self.reason_codes, AdaptationReasonCode))
        object.__setattr__(self, "warning_codes", _validate_codes("warning_codes", self.warning_codes, AdaptationWarningCode))
