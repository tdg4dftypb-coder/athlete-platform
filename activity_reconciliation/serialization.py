"""Canonical serialization for immutable activity reconciliation results."""
from __future__ import annotations

from typing import Any

from activity_reconciliation.models import ReconciliationResult


class ReconciliationResultSerializer:
    def serialize(self, result: ReconciliationResult) -> dict[str, Any]:
        return {
            "reconciliation_id": result.reconciliation_id,
            "policy_version": result.policy_version,
            "target_local_date": result.target_local_date.isoformat(),
            "timezone_name": result.timezone_name,
            "finalized": result.finalized,
            "plan_id": result.plan_id,
            "plan_version": result.plan_version,
            "evaluated_at": result.evaluated_at.isoformat(),
            "input_fingerprint": result.input_fingerprint,
            "planned_session_ids": list(result.planned_session_ids),
            "activity_event_ids": list(result.activity_event_ids),
            "replacement_evidence": [
                {
                    "planned_session_id": evidence.planned_session_id,
                    "activity_event_id": evidence.activity_event_id,
                    "source": evidence.source,
                    "reason_code": evidence.reason_code,
                    "schema_version": evidence.schema_version,
                }
                for evidence in result.replacement_evidence
            ],
            "items": [
                {
                    "match_status": item.match_status.value,
                    "planned_session_id": item.planned_session_id,
                    "activity": None if item.activity is None else {
                        "event_id": item.activity.event_id,
                        "source_type": item.activity.source_type,
                        "source_key": item.activity.source_key,
                    },
                    "candidate_session_ids": list(item.candidate_session_ids),
                    "candidate_activity_event_ids": list(
                        item.candidate_activity_event_ids
                    ),
                    "execution_outcome": (
                        None
                        if item.execution_outcome is None
                        else item.execution_outcome.value
                    ),
                    "completion_percent": item.completion_percent,
                    "reason_codes": list(item.reason_codes),
                    "warning_codes": list(item.warning_codes),
                }
                for item in result.items
            ],
        }
