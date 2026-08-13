"""Read-only latest Production Runtime visibility projection for HTTP clients."""
from __future__ import annotations

from pathlib import Path
import re

import duckdb

from plan_adaptation.models import AdaptationEvaluationStatus
from plan_adaptation.persistence import AdaptationAuditCodec, PlanRevisionStatus
from production_runtime.models import RuntimePhase


VISIBILITY_SCHEMA_VERSION = "1.0"
VISIBLE_PHASES = (
    RuntimePhase.PLAN_PRESCRIPTION,
    RuntimePhase.PLAN_HORIZON_CONTINUITY,
    RuntimePhase.PLAN_ADAPTATION,
    RuntimePhase.MORNING_BRIEFING,
    RuntimePhase.PUBLICATION,
)
_PLAN_ARTIFACT = re.compile(r"^training-plan:(.+):v([1-9][0-9]*)$")


class ProductionRuntimeVisibilityError(RuntimeError):
    pass


class EmptyAdaptationEntryReader:
    def get_entry(self, _adaptation_id):
        return None


class DuckDbPlanAdaptationEntryReader:
    """Strictly read-only decoder for already-existing Stage 29 artifacts."""
    def __init__(self, path):
        self._path = Path(path)
        self._codec = AdaptationAuditCodec()

    def get_entry(self, adaptation_id):
        if not self._path.is_file():
            return None
        connection = duckdb.connect(str(self._path), read_only=True)
        try:
            tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
            required = {"adaptation_evaluations", "plan_revision_proposals", "plan_revision_records"}
            if not required.issubset(tables):
                raise ProductionRuntimeVisibilityError("adaptation persistence schema is incomplete")
            evaluation_row = connection.execute(
                "SELECT payload_json FROM adaptation_evaluations WHERE adaptation_id=?",
                [adaptation_id],
            ).fetchone()
            if evaluation_row is None:
                return None
            proposal_row = connection.execute(
                "SELECT payload_json FROM plan_revision_proposals WHERE adaptation_id=?",
                [adaptation_id],
            ).fetchone()
            revision_row = connection.execute(
                "SELECT payload_json FROM plan_revision_records WHERE adaptation_id=?",
                [adaptation_id],
            ).fetchone()
            return (
                self._codec.decode_evaluation(evaluation_row[0]),
                None if proposal_row is None else self._codec.decode_proposal(proposal_row[0]),
                None if revision_row is None else self._codec.decode_revision(revision_row[0]),
            )
        finally:
            connection.close()


class ProductionRuntimeVisibilityReader:
    def __init__(self, runtime_reader, plan_repository, adaptation_reader=None):
        self._runtime = runtime_reader
        self._plans = plan_repository
        self._adaptation = adaptation_reader or EmptyAdaptationEntryReader()

    def get_latest_payload(self):
        snapshot = self._runtime.get_latest()
        if snapshot is None:
            return {"schema_version": VISIBILITY_SCHEMA_VERSION, "runtime": None}
        phases = {phase.phase: phase for phase in snapshot.phases if phase.present}
        related_plan = self._related_plan(snapshot, phases)
        return {
            "schema_version": VISIBILITY_SCHEMA_VERSION,
            "runtime": {
                "runtime_id": snapshot.runtime_id,
                "logical_execution_key": snapshot.logical_execution_key,
                "revision": snapshot.revision,
                "target_date": snapshot.target_local_date.isoformat(),
                "status": snapshot.status.value,
                "started_at": snapshot.started_at_utc.isoformat(),
                "completed_at": None if snapshot.completed_at_utc is None else snapshot.completed_at_utc.isoformat(),
                "failure_code": None if snapshot.failure is None else snapshot.failure.code,
                "plan": None if related_plan is None else self._plan_payload(related_plan),
                "phases": {
                    phase.value: self._phase_payload(phase, phases.get(phase))
                    for phase in VISIBLE_PHASES
                },
            },
        }

    def _phase_payload(self, phase_name, phase):
        if phase is None:
            return {"available": False}
        payload = {
            "available": True,
            "status": phase.status.value,
            "changed_state": phase.changed_state,
            "codes": list(phase.warning_codes),
            "artifact_ids": list(phase.artifact_ids),
        }
        if phase_name is RuntimePhase.PLAN_HORIZON_CONTINUITY:
            payload["continuity"] = self._continuity_payload(phase)
        if phase_name is RuntimePhase.PLAN_ADAPTATION:
            payload["adaptation"] = self._adaptation_payload(phase)
        return payload

    def _continuity_payload(self, phase):
        artifacts = (self._parse_plan_artifact(value) for value in phase.artifact_ids)
        artifact = next((value for value in artifacts if value is not None), None)
        if artifact is None:
            return self._empty_transition("unresolvable")
        plan_id, result_version = artifact
        result = self._plans.get_by_id_version(plan_id, result_version)
        source = self._plans.get_by_id_version(plan_id, result_version - 1) if phase.changed_state and result_version > 1 else result
        return {
            "artifact_status": "resolvable" if result is not None else "unresolvable",
            "source_plan_version": None if source is None else source.version,
            "result_plan_version": None if result is None else result.version,
            "source_coverage_end": None if source is None else source.end_date.isoformat(),
            "result_coverage_end": None if result is None else result.end_date.isoformat(),
            "target_horizon_days": None,
            "target_date": None,
        }

    def _adaptation_payload(self, phase):
        if not phase.artifact_ids:
            return self._empty_adaptation("unavailable")
        try:
            entry = self._adaptation.get_entry(phase.artifact_ids[0])
        except Exception:
            return self._empty_adaptation("corrupt")
        if entry is None:
            return self._empty_adaptation("unresolvable")
        evaluation, proposal, revision = entry
        if evaluation.status is AdaptationEvaluationStatus.NO_CHANGE:
            outcome = "NO_CHANGE"
        elif revision is not None and revision.status is PlanRevisionStatus.APPLIED:
            outcome = "APPLIED"
        elif revision is not None and revision.status is PlanRevisionStatus.REJECTED:
            outcome = "REJECTED"
        else:
            outcome = "CHANGE_PROPOSED"
        result_plan = None
        artifact_status = "resolvable"
        if revision is not None and revision.status is PlanRevisionStatus.APPLIED:
            result_plan = self._plans.get_by_id_version(revision.result_plan_id, revision.result_plan_version)
            if result_plan is None:
                artifact_status = "unresolvable"
        return {
            "artifact_status": artifact_status,
            "outcome": outcome,
            "source_plan_id": evaluation.source_plan_id,
            "source_plan_version": evaluation.source_plan_version,
            "result_plan_id": None if revision is None else revision.result_plan_id,
            "result_plan_version": None if revision is None else revision.result_plan_version,
            "actions": sorted({change.action.value for change in evaluation.proposed_changes}),
            "reason_codes": [reason.value for reason in evaluation.reason_codes],
            "failure_code": None if revision is None or revision.failure_code is None else revision.failure_code.value,
        }

    def _related_plan(self, snapshot, phases):
        adaptation = phases.get(RuntimePhase.PLAN_ADAPTATION)
        if adaptation is not None and adaptation.artifact_ids:
            try:
                entry = self._adaptation.get_entry(adaptation.artifact_ids[0])
            except Exception:
                entry = None
            if entry is not None:
                evaluation, _proposal, revision = entry
                if revision is not None and revision.status is PlanRevisionStatus.APPLIED:
                    plan = self._plans.get_by_id_version(revision.result_plan_id, revision.result_plan_version)
                    if plan is not None:
                        return plan
                return self._plans.get_by_id_version(evaluation.source_plan_id, evaluation.source_plan_version)
        continuity = phases.get(RuntimePhase.PLAN_HORIZON_CONTINUITY)
        if continuity is not None:
            for value in continuity.artifact_ids:
                parsed = self._parse_plan_artifact(value)
                if parsed is not None:
                    plan = self._plans.get_by_id_version(*parsed)
                    if plan is not None:
                        return plan
        if snapshot.artifact_references.training_plan_id:
            return self._plans.get_by_id(snapshot.artifact_references.training_plan_id)
        return None

    @staticmethod
    def _parse_plan_artifact(value):
        match = _PLAN_ARTIFACT.fullmatch(value)
        return None if match is None else (match.group(1), int(match.group(2)))

    @staticmethod
    def _plan_payload(plan):
        return {"plan_id": plan.plan_id, "version": plan.version,
                "coverage_start": plan.start_date.isoformat(), "coverage_end": plan.end_date.isoformat()}

    @staticmethod
    def _empty_transition(status):
        return {"artifact_status": status, "source_plan_version": None, "result_plan_version": None,
                "source_coverage_end": None, "result_coverage_end": None,
                "target_horizon_days": None, "target_date": None}

    @staticmethod
    def _empty_adaptation(status):
        return {"artifact_status": status, "outcome": None, "source_plan_id": None,
                "source_plan_version": None, "result_plan_id": None, "result_plan_version": None,
                "actions": [], "reason_codes": [], "failure_code": None}
