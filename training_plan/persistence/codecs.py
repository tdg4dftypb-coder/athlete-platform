"""Canonical JSON codecs for TrainingPlan and FinalSessionPrescription domain models."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from typing import Any

from training_plan.models import (
    PlannedSession,
    PlannedSessionKind,
    TrainingPlan,
)
from training_plan.prescription import (
    FinalSessionPrescription,
    PrescriptionDisposition,
)
from training_plan.repository import TrainingPlanDataError


class TrainingPlanCodec:
    """Canonical JSON codec for TrainingPlan."""

    SCHEMA_VERSION: str = "1.0"

    def encode(self, plan: TrainingPlan) -> str:
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "plan_id": plan.plan_id,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "version": plan.version,
            "generated_at": plan.generated_at.isoformat(),
            "supersedes_plan_id": plan.supersedes_plan_id,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "date": s.date.isoformat(),
                    "kind": s.kind.value,
                    "session_type": s.session_type,
                    "duration_minutes": s.duration_minutes,
                    "target_tss": s.target_tss,
                    "intensity": s.intensity,
                    "priority": s.priority,
                    "rationale": list(s.rationale),
                }
                for s in plan.sessions
            ],
        }
        return json.dumps(data, sort_keys=True, ensure_ascii=False)

    def decode(self, payload_json: str) -> TrainingPlan:
        try:
            data = json.loads(payload_json)
            sessions = []
            for item in data["sessions"]:
                gen_dt = date.fromisoformat(item["date"])
                s = PlannedSession(
                    session_id=item["session_id"],
                    date=gen_dt,
                    kind=PlannedSessionKind(item["kind"]),
                    session_type=item["session_type"],
                    duration_minutes=item["duration_minutes"],
                    target_tss=item["target_tss"],
                    intensity=item["intensity"],
                    priority=item["priority"],
                    rationale=tuple(item["rationale"]),
                )
                sessions.append(s)

            gen_at = datetime.fromisoformat(data["generated_at"])
            if gen_at.tzinfo is None:
                gen_at = gen_at.replace(tzinfo=timezone.utc)

            return TrainingPlan(
                plan_id=data["plan_id"],
                start_date=date.fromisoformat(data["start_date"]),
                end_date=date.fromisoformat(data["end_date"]),
                version=data["version"],
                generated_at=gen_at,
                sessions=tuple(sessions),
                supersedes_plan_id=data.get("supersedes_plan_id"),
            )
        except Exception as e:
            raise TrainingPlanDataError(f"Failed to decode TrainingPlan JSON payload: {e}") from e


class FinalSessionPrescriptionCodec:
    """Canonical JSON codec for FinalSessionPrescription."""

    SCHEMA_VERSION: str = "1.0"

    def encode(self, prescription: FinalSessionPrescription) -> str:
        s = prescription.source_session
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "prescription_id": prescription.prescription_id,
            "plan_id": prescription.plan_id,
            "decision_id": prescription.decision_id,
            "disposition": prescription.disposition.value,
            "prescribed_kind": prescription.prescribed_kind.value if prescription.prescribed_kind else None,
            "prescribed_session_type": prescription.prescribed_session_type,
            "prescribed_duration_minutes": prescription.prescribed_duration_minutes,
            "prescribed_target_tss": prescription.prescribed_target_tss,
            "prescribed_intensity": prescription.prescribed_intensity,
            "reason_codes": list(prescription.reason_codes),
            "generated_at": prescription.generated_at.isoformat(),
            "reconciliation_policy_version": prescription.reconciliation_policy_version,
            "source_session": {
                "session_id": s.session_id,
                "date": s.date.isoformat(),
                "kind": s.kind.value,
                "session_type": s.session_type,
                "duration_minutes": s.duration_minutes,
                "target_tss": s.target_tss,
                "intensity": s.intensity,
                "priority": s.priority,
                "rationale": list(s.rationale),
            },
        }
        return json.dumps(data, sort_keys=True, ensure_ascii=False)

    def decode(self, payload_json: str) -> FinalSessionPrescription:
        try:
            data = json.loads(payload_json)
            src_raw = data["source_session"]
            source_session = PlannedSession(
                session_id=src_raw["session_id"],
                date=date.fromisoformat(src_raw["date"]),
                kind=PlannedSessionKind(src_raw["kind"]),
                session_type=src_raw["session_type"],
                duration_minutes=src_raw["duration_minutes"],
                target_tss=src_raw["target_tss"],
                intensity=src_raw["intensity"],
                priority=src_raw["priority"],
                rationale=tuple(src_raw["rationale"]),
            )

            gen_at = datetime.fromisoformat(data["generated_at"])
            if gen_at.tzinfo is None:
                gen_at = gen_at.replace(tzinfo=timezone.utc)

            p_kind = PlannedSessionKind(data["prescribed_kind"]) if data.get("prescribed_kind") else None

            return FinalSessionPrescription(
                prescription_id=data["prescription_id"],
                plan_id=data["plan_id"],
                decision_id=data["decision_id"],
                source_session=source_session,
                disposition=PrescriptionDisposition(data["disposition"]),
                prescribed_kind=p_kind,
                prescribed_session_type=data.get("prescribed_session_type"),
                prescribed_duration_minutes=data.get("prescribed_duration_minutes"),
                prescribed_target_tss=data.get("prescribed_target_tss"),
                prescribed_intensity=data.get("prescribed_intensity"),
                reason_codes=tuple(data.get("reason_codes", [])),
                generated_at=gen_at,
                reconciliation_policy_version=data.get("reconciliation_policy_version", "1.0"),
            )
        except Exception as e:
            raise TrainingPlanDataError(f"Failed to decode FinalSessionPrescription JSON payload: {e}") from e
