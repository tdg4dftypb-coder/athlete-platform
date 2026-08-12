"""Conservative versioned activity-to-session matching policy."""
from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
from zoneinfo import ZoneInfo

from athlete.memory.models import AthleteMemoryEvent, AthleteMemoryEventType
from training_plan.models import PlannedSession, PlannedSessionKind, TrainingPlan
from activity_reconciliation.models import (
    ActivityExecutionOutcome, ActivityReference, MatchStatus,
    ReconciliationItem, ReconciliationResult, ReplacementEvidence,
)


CYCLING_SESSION_TYPES = frozenset({
    "VO2", "SST", "THRESHOLD", "TEMPO", "ENDURANCE", "CADENCE", "RECOVERY",
    "CYCLING", "BIKE",
})
CYCLING_SPORTS = frozenset({"cycling"})
SWIM_SESSION_TYPES = frozenset({"SWIM", "SWIMMING"})
SWIM_SPORTS = frozenset({"swim", "swimming"})
STRENGTH_SESSION_TYPES = frozenset({"STRENGTH", "CROSSFIT"})
STRENGTH_SPORTS = frozenset({"strength", "crossfit"})


class ActivitySessionReconciler:
    POLICY_VERSION = "1.0"

    def reconcile(
        self,
        plan: TrainingPlan,
        activities: tuple[AthleteMemoryEvent, ...],
        target_date: date,
        finalized: bool,
        evaluated_at: datetime,
        timezone_name: str = "Europe/Warsaw",
        replacement_evidence: tuple[ReplacementEvidence, ...] = (),
    ) -> ReconciliationResult:
        if not isinstance(plan, TrainingPlan):
            raise TypeError("plan must be TrainingPlan")
        if type(target_date) is not date:
            raise TypeError("target_date must be date")
        if not isinstance(finalized, bool):
            raise TypeError("finalized must be bool")
        if not isinstance(evaluated_at, datetime):
            raise TypeError("evaluated_at must be datetime")
        zone = ZoneInfo(timezone_name)
        planned = tuple(s for s in plan.sessions if s.date == target_date)
        canonical_activities = self._canonical_activities(activities, target_date, zone)
        activity_by_id = {event.event_id: event for event in canonical_activities}
        planned_by_id = {session.session_id: session for session in planned}

        replacements = tuple(sorted(
            replacement_evidence,
            key=lambda item: (item.planned_session_id, item.activity_event_id),
        ))
        replaced_sessions: set[str] = set()
        replaced_activities: set[str] = set()
        items: list[ReconciliationItem] = [
            ReconciliationItem(
                MatchStatus.UNMATCHED_PLANNED,
                planned_session_id=session.session_id,
                reason_codes=("intentional_rest",),
            )
            for session in planned
            if session.kind is PlannedSessionKind.REST
        ]
        for evidence in replacements:
            session = planned_by_id.get(evidence.planned_session_id)
            event = activity_by_id.get(evidence.activity_event_id)
            if session is None or event is None:
                raise ValueError("replacement evidence references unknown target-date input")
            if session.kind is PlannedSessionKind.REST:
                raise ValueError("replacement evidence cannot reference REST")
            if session.session_id in replaced_sessions or event.event_id in replaced_activities:
                raise ValueError("replacement evidence must be one-to-one")
            replaced_sessions.add(session.session_id)
            replaced_activities.add(event.event_id)
            items.append(ReconciliationItem(
                match_status=MatchStatus.MATCHED,
                planned_session_id=session.session_id,
                activity=self._reference(event),
                execution_outcome=ActivityExecutionOutcome.REPLACED,
                reason_codes=("same_local_date", "explicit_replacement"),
            ))

        training = tuple(s for s in planned if s.kind is PlannedSessionKind.TRAINING and s.session_id not in replaced_sessions)
        available = tuple(e for e in canonical_activities if e.event_id not in replaced_activities)
        edges = {
            session.session_id: tuple(
                event.event_id for event in available if self._sport_compatible(session, event)
            )
            for session in training
        }
        reverse = {
            event.event_id: tuple(
                session.session_id for session in training
                if event.event_id in edges[session.session_id]
            )
            for event in available
        }
        matched_sessions: set[str] = set()
        matched_activities: set[str] = set()
        ambiguous_sessions = {sid for sid, aids in edges.items() if aids and not (
            len(aids) == 1 and len(reverse[aids[0]]) == 1
        )}
        ambiguous_activities = {aid for aid, sids in reverse.items() if sids and not (
            len(sids) == 1 and len(edges[sids[0]]) == 1
        )}

        for session in training:
            candidates = edges[session.session_id]
            if len(candidates) == 1 and len(reverse[candidates[0]]) == 1:
                event = activity_by_id[candidates[0]]
                matched_sessions.add(session.session_id)
                matched_activities.add(event.event_id)
                outcome, percent, reasons, warnings = self._completion(session, event)
                items.append(ReconciliationItem(
                    MatchStatus.MATCHED, session.session_id, self._reference(event),
                    execution_outcome=outcome, completion_percent=percent,
                    reason_codes=("same_local_date", "sport_compatible", "unique_candidate") + reasons,
                    warning_codes=warnings,
                ))

        for session in training:
            if session.session_id in matched_sessions or session.session_id in replaced_sessions:
                continue
            candidates = edges[session.session_id]
            if session.session_id in ambiguous_sessions:
                items.append(ReconciliationItem(
                    MatchStatus.AMBIGUOUS, planned_session_id=session.session_id,
                    candidate_activity_event_ids=candidates,
                    reason_codes=("same_local_date", "multiple_candidate_activities"),
                ))
            else:
                items.append(ReconciliationItem(
                    MatchStatus.UNMATCHED_PLANNED, planned_session_id=session.session_id,
                    execution_outcome=ActivityExecutionOutcome.SKIPPED if finalized else None,
                    reason_codes=("planned_session_unmatched",) + (() if finalized else ("target_date_not_finalized",)),
                ))

        for event in available:
            if event.event_id in matched_activities or event.event_id in replaced_activities:
                continue
            candidates = reverse[event.event_id]
            if event.event_id in ambiguous_activities:
                items.append(ReconciliationItem(
                    MatchStatus.AMBIGUOUS, activity=self._reference(event),
                    candidate_session_ids=candidates,
                    reason_codes=("same_local_date", "multiple_candidate_sessions"),
                ))
            else:
                items.append(ReconciliationItem(
                    MatchStatus.UNMATCHED_ACTIVITY, activity=self._reference(event),
                    execution_outcome=ActivityExecutionOutcome.UNPLANNED,
                    reason_codes=("activity_unmatched",),
                ))

        items.sort(key=lambda item: (
            item.planned_session_id or "~",
            item.activity.event_id if item.activity else "~",
            item.match_status.value,
        ))
        fingerprint = self._fingerprint(plan, target_date, finalized, timezone_name, planned, canonical_activities, replacements)
        return ReconciliationResult(
            reconciliation_id=f"reconciliation:{fingerprint}",
            input_fingerprint=fingerprint,
            policy_version=self.POLICY_VERSION,
            target_local_date=target_date,
            timezone_name=timezone_name,
            plan_id=plan.plan_id,
            plan_version=plan.version,
            finalized=finalized,
            planned_session_ids=tuple(s.session_id for s in planned),
            activity_event_ids=tuple(e.event_id for e in canonical_activities),
            items=tuple(items),
            replacement_evidence=replacements,
            evaluated_at=evaluated_at,
        )

    @staticmethod
    def _canonical_activities(activities, target_date, zone):
        selected = []
        seen = set()
        for event in activities:
            if not isinstance(event, AthleteMemoryEvent):
                raise TypeError("activities must contain AthleteMemoryEvent")
            if event.event_type is not AthleteMemoryEventType.ACTIVITY_RECORDED:
                continue
            if event.event_id in seen:
                continue
            start = datetime.fromisoformat(event.payload["activity"]["start"])
            local_date = start.replace(tzinfo=zone).date() if start.tzinfo is None else start.astimezone(zone).date()
            if local_date == target_date:
                selected.append(event)
                seen.add(event.event_id)
        return tuple(sorted(selected, key=lambda event: event.event_id))

    @staticmethod
    def _sport_compatible(session, event):
        session_type = session.session_type
        sport = event.payload["activity"].get("sport")
        if not isinstance(sport, str):
            return False
        sport = sport.strip().lower()
        return (
            (session_type in CYCLING_SESSION_TYPES and sport in CYCLING_SPORTS)
            or (session_type in SWIM_SESSION_TYPES and sport in SWIM_SPORTS)
            or (session_type in STRENGTH_SESSION_TYPES and sport in STRENGTH_SPORTS)
        )

    @staticmethod
    def _completion(session, event):
        duration = event.payload["activity"].get("duration")
        if duration is None:
            return None, None, (), ("activity_duration_missing",)
        percent = min(100.0, float(duration) / (session.duration_minutes * 60) * 100.0)
        if percent >= 90.0:
            return ActivityExecutionOutcome.COMPLETED, percent, ("duration_at_least_90_percent",), ()
        return ActivityExecutionOutcome.PARTIAL, percent, ("duration_below_90_percent",), ()

    @staticmethod
    def _reference(event):
        return ActivityReference(event.event_id, event.source_type, event.source_key)

    def _fingerprint(self, plan, target_date, finalized, timezone_name, planned, activities, replacements):
        payload = {
            "policy_version": self.POLICY_VERSION,
            "target_date": target_date.isoformat(), "timezone": timezone_name,
            "plan_id": plan.plan_id, "plan_version": plan.version, "finalized": finalized,
            "sessions": [{
                "session_id": session.session_id,
                "date": session.date.isoformat(),
                "kind": session.kind.value,
                "session_type": session.session_type,
                "duration_minutes": session.duration_minutes,
                "target_tss": session.target_tss,
                "intensity": session.intensity,
                "priority": session.priority,
                "rationale": list(session.rationale),
            } for session in planned],
            "activities": [{"event_id": e.event_id, "source_type": e.source_type,
                            "source_key": e.source_key, "schema_version": e.schema_version,
                            "payload": e.payload} for e in activities],
            "replacements": [e.__dict__ for e in replacements],
        }
        return "sha256:" + sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
