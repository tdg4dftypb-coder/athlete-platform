"""Deterministic normalization boundary for Stage 29.2 adaptation evidence."""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime, timedelta
from enum import Enum
from hashlib import sha256
import json

from activity_reconciliation.models import MatchStatus, ReconciliationItem, ReconciliationResult
from application.athlete_assessment import AthleteAssessment
from training_plan.models import PlannedSession, TrainingPlan

from plan_adaptation.context import (
    AdaptationConstraint,
    AdaptationContext,
    AdaptationHistoryDay,
    AdaptationTrainingLoad,
    WeeklyRhythm,
)
from plan_adaptation.models import AdaptationContextWindow, AdaptationWarningCode, AdaptationWindow


class AdaptationContextBuildError(ValueError):
    """Raised when structural source-plan requirements make a context impossible."""


def _semantic_value(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_semantic_value(item) for item in value]
    if is_dataclass(value):
        excluded = {
            "as_of",
            "evaluated_at",
            "built_at",
            "input_fingerprint",
            "reconciliation_id",
        }
        return {
            item.name: _semantic_value(getattr(value, item.name))
            for item in fields(value)
            if item.name not in excluded
        }
    return value


def _item_key(item: ReconciliationItem) -> str:
    return json.dumps(_semantic_value(item), sort_keys=True, separators=(",", ":"))


def _canonical_reconciliation(result: ReconciliationResult) -> ReconciliationResult:
    canonical_items = []
    for item in result.items:
        canonical_items.append(replace(
            item,
            candidate_session_ids=tuple(sorted(item.candidate_session_ids)),
            candidate_activity_event_ids=tuple(sorted(item.candidate_activity_event_ids)),
            reason_codes=tuple(sorted(item.reason_codes)),
            warning_codes=tuple(sorted(item.warning_codes)),
        ))
    return replace(
        result,
        planned_session_ids=tuple(sorted(result.planned_session_ids)),
        activity_event_ids=tuple(sorted(result.activity_event_ids)),
        items=tuple(sorted(canonical_items, key=_item_key)),
        replacement_evidence=tuple(sorted(
            result.replacement_evidence,
            key=lambda item: (item.planned_session_id, item.activity_event_id),
        )),
    )


class AdaptationContextBuilder:
    """Builds policy input only; it never evaluates or proposes adaptation actions."""

    def build(
        self,
        *,
        evaluation_date: date,
        source_plan: TrainingPlan,
        historical_planned_sessions: tuple[PlannedSession, ...],
        reconciliations: tuple[ReconciliationResult, ...],
        training_load: AdaptationTrainingLoad | None,
        athlete_state: AthleteAssessment | None,
        constraints: tuple[AdaptationConstraint, ...] | None,
        weekly_rhythm: WeeklyRhythm | None,
        built_at: datetime,
    ) -> AdaptationContext:
        context_window = AdaptationContextWindow.canonical(evaluation_date)
        mutation_window = AdaptationWindow.canonical(evaluation_date)
        if not isinstance(source_plan, TrainingPlan):
            raise TypeError("source_plan must be TrainingPlan")
        if source_plan.start_date > mutation_window.mutation_start or source_plan.end_date < mutation_window.mutation_end:
            raise AdaptationContextBuildError("source plan must cover the complete D+1 through D+7 mutation window")
        if not isinstance(historical_planned_sessions, tuple):
            raise TypeError("historical_planned_sessions must be tuple")
        if any(not isinstance(session, PlannedSession) for session in historical_planned_sessions):
            raise TypeError("historical_planned_sessions must contain PlannedSession")
        if any(not (context_window.context_start <= session.date <= context_window.context_end) for session in historical_planned_sessions):
            raise ValueError("historical planned session lies outside D-7 through D")
        if len({session.session_id for session in historical_planned_sessions}) != len(historical_planned_sessions):
            raise ValueError("historical_planned_sessions contains duplicate session_id")
        if not isinstance(reconciliations, tuple):
            raise TypeError("reconciliations must be tuple")
        if any(not isinstance(result, ReconciliationResult) for result in reconciliations):
            raise TypeError("reconciliations must contain ReconciliationResult")
        if any(not (context_window.context_start <= result.target_local_date <= context_window.context_end) for result in reconciliations):
            raise ValueError("reconciliation lies outside D-7 through D")
        if len({result.target_local_date for result in reconciliations}) != len(reconciliations):
            raise ValueError("at most one reconciliation is allowed per historical day")
        if not isinstance(built_at, datetime):
            raise TypeError("built_at must be datetime")

        sessions_by_date: dict[date, list[PlannedSession]] = {}
        for session in historical_planned_sessions:
            sessions_by_date.setdefault(session.date, []).append(session)
        reconciliation_by_date = {
            result.target_local_date: _canonical_reconciliation(result)
            for result in reconciliations
        }
        historical_days = tuple(
            AdaptationHistoryDay(
                day=context_window.context_start + timedelta(days=offset),
                planned_sessions=tuple(sessions_by_date.get(context_window.context_start + timedelta(days=offset), ())),
                reconciliation=reconciliation_by_date.get(context_window.context_start + timedelta(days=offset)),
            )
            for offset in range(8)
        )
        future_sessions = tuple(sorted(
            (
                session for session in source_plan.sessions
                if mutation_window.mutation_start <= session.date <= mutation_window.mutation_end
            ),
            key=lambda session: (session.date, session.session_id),
        ))
        canonical_constraints = tuple(sorted(constraints or (), key=lambda item: item.constraint_id))
        if len({item.constraint_id for item in canonical_constraints}) != len(canonical_constraints):
            raise ValueError("constraints contains duplicate constraint_id")

        warnings = set()
        if any(day.reconciliation is None for day in historical_days):
            warnings.add(AdaptationWarningCode.RECONCILIATION_UNAVAILABLE)
        if any(day.is_ambiguous for day in historical_days):
            warnings.add(AdaptationWarningCode.RECONCILIATION_AMBIGUOUS)
        if any(
            day.reconciliation is not None and (
                not day.reconciliation.finalized
                or any(
                    item.match_status is MatchStatus.MATCHED and item.execution_outcome is None
                    for item in day.reconciliation.items
                )
            )
            for day in historical_days
        ):
            warnings.add(AdaptationWarningCode.RECONCILIATION_INCOMPLETE)
        if athlete_state is None:
            warnings.add(AdaptationWarningCode.ATHLETE_ASSESSMENT_UNAVAILABLE)
        if training_load is None or training_load.available_metric_count == 0:
            warnings.add(AdaptationWarningCode.TRAINING_LOAD_UNAVAILABLE)
        elif training_load.available_metric_count < 4:
            warnings.add(AdaptationWarningCode.TRAINING_LOAD_PARTIAL)
        if weekly_rhythm is None:
            warnings.add(AdaptationWarningCode.WEEKLY_RHYTHM_UNAVAILABLE)
        if constraints is None:
            warnings.add(AdaptationWarningCode.ATHLETE_CONSTRAINTS_UNAVAILABLE)

        semantic_payload = {
            "evaluation_date": evaluation_date.isoformat(),
            "source_plan_id": source_plan.plan_id,
            "source_plan_version": source_plan.version,
            "historical_days": _semantic_value(historical_days),
            "future_sessions": _semantic_value(future_sessions),
            "training_load": _semantic_value(training_load),
            "athlete_state": _semantic_value(athlete_state),
            "constraints": _semantic_value(canonical_constraints),
            "weekly_rhythm": _semantic_value(weekly_rhythm),
            "warning_codes": sorted(warning.value for warning in warnings),
        }
        fingerprint = "sha256:" + sha256(
            json.dumps(semantic_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return AdaptationContext(
            evaluation_date=evaluation_date,
            context_window=context_window,
            mutation_window=mutation_window,
            source_plan_id=source_plan.plan_id,
            source_plan_version=source_plan.version,
            historical_days=historical_days,
            future_sessions=future_sessions,
            training_load=training_load,
            athlete_state=athlete_state,
            constraints=canonical_constraints,
            weekly_rhythm=weekly_rhythm,
            warning_codes=tuple(warnings),
            input_fingerprint=fingerprint,
            built_at=built_at,
        )
