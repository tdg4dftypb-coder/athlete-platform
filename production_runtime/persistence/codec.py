"""Canonical JSON codec for immutable runtime audit revisions."""
from __future__ import annotations

from datetime import date, datetime
import json

from production_runtime.models import (
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimeFailure,
    RuntimePhase,
    RuntimePhaseResult,
    RuntimeStatus,
    RuntimeWarning,
    SourceWatermark,
)
from production_runtime.repository import RuntimeAuditDataError


class RuntimeAuditCodec:
    SCHEMA_VERSION = "1.0"

    def encode(self, result: ProductionDailyRuntimeResult) -> str:
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "runtime_id": result.runtime_id,
            "logical_execution_key": result.logical_execution_key,
            "revision": result.revision,
            "contract_version": result.contract_version,
            "target_local_date": result.target_local_date.isoformat(),
            "timezone_name": result.timezone_name,
            "started_at_utc": result.started_at_utc.isoformat(),
            "completed_at_utc": result.completed_at_utc.isoformat() if result.completed_at_utc else None,
            "status": result.status.value,
            "phases": [
                {
                    "phase": item.phase.value,
                    "status": item.status.value,
                    "started_at_utc": item.started_at_utc.isoformat(),
                    "completed_at_utc": item.completed_at_utc.isoformat(),
                    "changed_state": item.changed_state,
                    "item_count": item.item_count,
                    "artifact_ids": list(item.artifact_ids),
                    "warning_codes": list(item.warning_codes),
                }
                for item in result.phases
            ],
            "decision_id": result.decision_id,
            "training_plan_id": result.training_plan_id,
            "prescription_id": result.prescription_id,
            "morning_briefing_available": result.morning_briefing_available,
            "activities_discovered": result.activities_discovered,
            "activity_facts_created": result.activity_facts_created,
            "activities_already_present": result.activities_already_present,
            "reconciliations_created": result.reconciliations_created,
            "source_watermarks": [
                {
                    "source": item.source,
                    "kind": item.kind,
                    "value": item.value,
                    "observed_at_utc": item.observed_at_utc.isoformat() if item.observed_at_utc else None,
                }
                for item in result.source_watermarks
            ],
            "warnings": [
                {"code": item.code, "detail": item.detail, "source": item.source}
                for item in result.warnings
            ],
            "failure": None if result.failure is None else {
                "code": result.failure.code,
                "phase": result.failure.phase.value if result.failure.phase else None,
                "detail": result.failure.detail,
            },
        }
        return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def decode(self, payload_json: str) -> ProductionDailyRuntimeResult:
        try:
            data = json.loads(payload_json)
            if data["schema_version"] != self.SCHEMA_VERSION:
                raise ValueError(f"unsupported schema_version '{data['schema_version']}'")
            phases = tuple(
                RuntimePhaseResult(
                    phase=RuntimePhase(item["phase"]),
                    status=PhaseStatus(item["status"]),
                    started_at_utc=datetime.fromisoformat(item["started_at_utc"]),
                    completed_at_utc=datetime.fromisoformat(item["completed_at_utc"]),
                    changed_state=item["changed_state"],
                    item_count=item.get("item_count"),
                    artifact_ids=tuple(item.get("artifact_ids", ())),
                    warning_codes=tuple(item.get("warning_codes", ())),
                )
                for item in data.get("phases", ())
            )
            watermarks = tuple(
                SourceWatermark(
                    source=item["source"],
                    kind=item["kind"],
                    value=item["value"],
                    observed_at_utc=(
                        datetime.fromisoformat(item["observed_at_utc"])
                        if item.get("observed_at_utc") else None
                    ),
                )
                for item in data.get("source_watermarks", ())
            )
            warnings = tuple(
                RuntimeWarning(code=item["code"], detail=item.get("detail"), source=item.get("source"))
                for item in data.get("warnings", ())
            )
            failure_data = data.get("failure")
            failure = None if failure_data is None else RuntimeFailure(
                code=failure_data["code"],
                phase=RuntimePhase(failure_data["phase"]) if failure_data.get("phase") else None,
                detail=failure_data.get("detail"),
            )
            return ProductionDailyRuntimeResult(
                runtime_id=data["runtime_id"],
                logical_execution_key=data["logical_execution_key"],
                revision=data["revision"],
                contract_version=data["contract_version"],
                target_local_date=date.fromisoformat(data["target_local_date"]),
                timezone_name=data["timezone_name"],
                started_at_utc=datetime.fromisoformat(data["started_at_utc"]),
                completed_at_utc=(
                    datetime.fromisoformat(data["completed_at_utc"])
                    if data.get("completed_at_utc") else None
                ),
                status=RuntimeStatus(data["status"]),
                phases=phases,
                decision_id=data.get("decision_id"),
                training_plan_id=data.get("training_plan_id"),
                prescription_id=data.get("prescription_id"),
                morning_briefing_available=data.get("morning_briefing_available", False),
                activities_discovered=data.get("activities_discovered"),
                activity_facts_created=data.get("activity_facts_created"),
                activities_already_present=data.get("activities_already_present"),
                reconciliations_created=data.get("reconciliations_created"),
                source_watermarks=watermarks,
                warnings=warnings,
                failure=failure,
            )
        except Exception as error:
            raise RuntimeAuditDataError(f"Failed to decode runtime audit payload: {error}") from error
