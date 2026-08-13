"""Append-only Stage 29.5 adaptation audit persistence and read contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import threading

import duckdb

from plan_adaptation.models import (
    AdaptationAction, AdaptationContextWindow, AdaptationEvaluationStatus,
    AdaptationReasonCode, AdaptationWarningCode, AdaptationWindow,
    PlanAdaptationEvaluation, PlanRevisionProposal, SessionAdaptationChange,
)
from plan_adaptation.revision import PlanRevisionValidationCode
from training_plan.models import TrainingPlan
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository


class PlanRevisionStatus(Enum):
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class PlanRevisionRecord:
    revision_id: str
    proposal_id: str
    adaptation_id: str
    source_plan_id: str
    source_plan_version: int
    status: PlanRevisionStatus
    result_plan_id: str | None
    result_plan_version: int | None
    failure_code: PlanRevisionValidationCode | None
    input_fingerprint: str
    applied_at: datetime

    def __post_init__(self) -> None:
        applied = self.status is PlanRevisionStatus.APPLIED
        if applied != (self.result_plan_id is not None and self.result_plan_version is not None):
            raise ValueError("APPLIED requires result plan reference; REJECTED forbids it")
        if applied != (self.failure_code is None):
            raise ValueError("REJECTED requires failure_code; APPLIED forbids it")

    @classmethod
    def applied(cls, proposal: PlanRevisionProposal, adaptation_id: str, result: TrainingPlan, applied_at: datetime):
        semantic = f"{proposal.proposal_id}|APPLIED|{result.plan_id}|{result.version}"
        return cls("revision:sha256:" + sha256(semantic.encode()).hexdigest(), proposal.proposal_id,
                   adaptation_id, proposal.source_plan_id, proposal.source_plan_version,
                   PlanRevisionStatus.APPLIED, result.plan_id, result.version, None,
                   proposal.input_fingerprint, applied_at)

    @classmethod
    def rejected(cls, proposal: PlanRevisionProposal, adaptation_id: str,
                 failure_code: PlanRevisionValidationCode, applied_at: datetime):
        semantic = f"{proposal.proposal_id}|REJECTED|{failure_code.value}"
        return cls("revision:sha256:" + sha256(semantic.encode()).hexdigest(), proposal.proposal_id,
                   adaptation_id, proposal.source_plan_id, proposal.source_plan_version,
                   PlanRevisionStatus.REJECTED, None, None, failure_code,
                   proposal.input_fingerprint, applied_at)


@dataclass(frozen=True)
class AdaptationHistoryEntry:
    evaluation: PlanAdaptationEvaluation
    proposal: PlanRevisionProposal | None
    revision: PlanRevisionRecord | None

    def __post_init__(self):
        if self.evaluation.status is AdaptationEvaluationStatus.NO_CHANGE and (self.proposal or self.revision):
            raise ValueError("NO_CHANGE history cannot have proposal or revision")
        if self.revision is not None and self.proposal is None:
            raise ValueError("revision requires proposal")


class AdaptationPersistenceConflictError(RuntimeError):
    pass


class AdaptationPersistenceDataError(RuntimeError):
    pass


def _change_data(change):
    return {"session_id": change.session_id, "session_date": change.session_date.isoformat(),
            "action": change.action.value, "reason_codes": [x.value for x in change.reason_codes],
            "target_duration_minutes": change.target_duration_minutes,
            "target_intensity": change.target_intensity, "target_session_type": change.target_session_type}


def _change(raw):
    return SessionAdaptationChange(raw["session_id"], date.fromisoformat(raw["session_date"]),
        AdaptationAction(raw["action"]), tuple(AdaptationReasonCode(x) for x in raw["reason_codes"]),
        raw["target_duration_minutes"], raw["target_intensity"], raw["target_session_type"])


class AdaptationAuditCodec:
    SCHEMA_VERSION = "1.0"

    def encode_evaluation(self, value):
        return json.dumps({"schema_version": self.SCHEMA_VERSION, "adaptation_id": value.adaptation_id,
            "policy_version": value.policy_version, "status": value.status.value,
            "evaluation_date": value.evaluation_date.isoformat(),
            "context_start": value.context_window.context_start.isoformat(),
            "context_end": value.context_window.context_end.isoformat(),
            "mutation_start": value.mutation_window.mutation_start.isoformat(),
            "mutation_end": value.mutation_window.mutation_end.isoformat(),
            "source_plan_id": value.source_plan_id, "source_plan_version": value.source_plan_version,
            "changes": [_change_data(x) for x in value.proposed_changes],
            "reason_codes": [x.value for x in value.reason_codes], "warning_codes": [x.value for x in value.warning_codes],
            "input_fingerprint": value.input_fingerprint, "evaluated_at": value.evaluated_at.isoformat()}, sort_keys=True)

    def decode_evaluation(self, payload):
        d=json.loads(payload); self._schema(d)
        evaluation_date=date.fromisoformat(d["evaluation_date"])
        return PlanAdaptationEvaluation(d["adaptation_id"], d["policy_version"], AdaptationEvaluationStatus(d["status"]),
            evaluation_date, AdaptationContextWindow(evaluation_date,date.fromisoformat(d["context_start"]),date.fromisoformat(d["context_end"])),
            AdaptationWindow(evaluation_date,date.fromisoformat(d["mutation_start"]),date.fromisoformat(d["mutation_end"])),
            d["source_plan_id"],d["source_plan_version"],tuple(_change(x) for x in d["changes"]),
            tuple(AdaptationReasonCode(x) for x in d["reason_codes"]),tuple(AdaptationWarningCode(x) for x in d["warning_codes"]),
            d["input_fingerprint"],datetime.fromisoformat(d["evaluated_at"]))

    def encode_proposal(self, value):
        d=json.loads(self.encode_evaluation(PlanAdaptationEvaluation("x",value.policy_version,AdaptationEvaluationStatus.CHANGE_PROPOSED,
            value.evaluation_date,value.context_window,value.mutation_window,value.source_plan_id,value.source_plan_version,
            value.changes,value.reason_codes,value.warning_codes,value.input_fingerprint,value.evaluated_at)))
        d["proposal_id"]=value.proposal_id; d.pop("adaptation_id"); d.pop("status"); return json.dumps(d,sort_keys=True)

    def decode_proposal(self,payload):
        d=json.loads(payload); self._schema(d); ed=date.fromisoformat(d["evaluation_date"])
        return PlanRevisionProposal(d["proposal_id"],d["policy_version"],ed,d["source_plan_id"],d["source_plan_version"],
            AdaptationContextWindow(ed,date.fromisoformat(d["context_start"]),date.fromisoformat(d["context_end"])),
            AdaptationWindow(ed,date.fromisoformat(d["mutation_start"]),date.fromisoformat(d["mutation_end"])),
            tuple(_change(x) for x in d["changes"]),tuple(AdaptationReasonCode(x) for x in d["reason_codes"]),
            tuple(AdaptationWarningCode(x) for x in d["warning_codes"]),d["input_fingerprint"],datetime.fromisoformat(d["evaluated_at"]))

    def encode_revision(self,v):
        return json.dumps({"schema_version":self.SCHEMA_VERSION, **{k:(x.value if isinstance(x,Enum) else x.isoformat() if isinstance(x,datetime) else x) for k,x in v.__dict__.items()}},sort_keys=True)

    def decode_revision(self,payload):
        d=json.loads(payload); self._schema(d)
        return PlanRevisionRecord(d["revision_id"],d["proposal_id"],d["adaptation_id"],d["source_plan_id"],d["source_plan_version"],
            PlanRevisionStatus(d["status"]),d["result_plan_id"],d["result_plan_version"],
            None if d["failure_code"] is None else PlanRevisionValidationCode(d["failure_code"]),d["input_fingerprint"],datetime.fromisoformat(d["applied_at"]))

    def _schema(self,d):
        if d.get("schema_version") != self.SCHEMA_VERSION: raise ValueError("unsupported adaptation schema version")


class DuckDbPlanAdaptationRepository:
    def __init__(self, db_path):
        self._path=str(db_path); self._lock=threading.Lock(); self._codec=AdaptationAuditCodec(); self._ensure()
    def _connect(self):
        if self._path != ":memory:": Path(self._path).parent.mkdir(parents=True,exist_ok=True)
        return duckdb.connect(self._path)
    def _ensure(self):
        with self._lock:
            c=self._connect()
            try:
                c.execute("CREATE TABLE IF NOT EXISTS adaptation_evaluations (adaptation_id VARCHAR PRIMARY KEY,evaluation_date DATE,evaluated_at TIMESTAMP,payload_json VARCHAR NOT NULL)")
                c.execute("CREATE TABLE IF NOT EXISTS plan_revision_proposals (proposal_id VARCHAR PRIMARY KEY,adaptation_id VARCHAR UNIQUE NOT NULL,payload_json VARCHAR NOT NULL)")
                c.execute("CREATE TABLE IF NOT EXISTS plan_revision_records (revision_id VARCHAR PRIMARY KEY,proposal_id VARCHAR UNIQUE NOT NULL,adaptation_id VARCHAR UNIQUE NOT NULL,applied_at TIMESTAMP,payload_json VARCHAR NOT NULL)")
            finally:c.close()
    @staticmethod
    def _semantic_payload(payload, audit_fields):
        data=json.loads(payload)
        for field in audit_fields:data.pop(field,None)
        return json.dumps(data,sort_keys=True)
    def _save(self,table,key_col,key,payload,columns=(),values=(),audit_fields=()):
        with self._lock:
            c=self._connect()
            try:
                row=c.execute(f"SELECT payload_json FROM {table} WHERE {key_col}=?",[key]).fetchone()
                if row:
                    if self._semantic_payload(row[0],audit_fields) != self._semantic_payload(payload,audit_fields):
                        raise AdaptationPersistenceConflictError(f"{key} payload collision")
                    return False
                names=",".join((key_col,*columns,"payload_json")); marks=",".join("?" for _ in range(2+len(columns)))
                c.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})",[key,*values,payload]); return True
            finally:c.close()
    def save_evaluation(self,v): return self._save("adaptation_evaluations","adaptation_id",v.adaptation_id,self._codec.encode_evaluation(v),("evaluation_date","evaluated_at"),(v.evaluation_date,v.evaluated_at),("evaluated_at",))
    def save_proposal(self,adaptation_id,v): return self._save("plan_revision_proposals","proposal_id",v.proposal_id,self._codec.encode_proposal(v),("adaptation_id",),(adaptation_id,),("evaluated_at",))
    def save_revision(self,v): return self._save("plan_revision_records","revision_id",v.revision_id,self._codec.encode_revision(v),("proposal_id","adaptation_id","applied_at"),(v.proposal_id,v.adaptation_id,v.applied_at),("applied_at",))
    def _get(self,table,col,key,decode):
        with self._lock:
            c=self._connect()
            try:
                row=c.execute(f"SELECT payload_json FROM {table} WHERE {col}=?",[key]).fetchone(); return None if row is None else decode(row[0])
            finally:c.close()
    def get_evaluation_by_id(self,key): return self._get("adaptation_evaluations","adaptation_id",key,self._codec.decode_evaluation)
    def get_proposal_by_id(self,key): return self._get("plan_revision_proposals","proposal_id",key,self._codec.decode_proposal)
    def get_revision_by_id(self,key): return self._get("plan_revision_records","revision_id",key,self._codec.decode_revision)
    def get_revision_for_adaptation(self,key): return self._get("plan_revision_records","adaptation_id",key,self._codec.decode_revision)
    def get_latest_evaluation(self): return self._latest(None)
    def get_latest_evaluation_for_date(self,d): return self._latest(d)
    def _latest(self,d):
        with self._lock:
            c=self._connect()
            try:
                where="" if d is None else "WHERE evaluation_date=?"; args=[] if d is None else [d]
                row=c.execute(f"SELECT payload_json FROM adaptation_evaluations {where} ORDER BY evaluation_date DESC,evaluated_at DESC,adaptation_id DESC LIMIT 1",args).fetchone()
                return None if row is None else self._codec.decode_evaluation(row[0])
            finally:c.close()
    def get_evaluation_history(self):
        with self._lock:
            c=self._connect()
            try:return tuple(self._codec.decode_evaluation(x[0]) for x in c.execute("SELECT payload_json FROM adaptation_evaluations ORDER BY evaluation_date,evaluated_at,adaptation_id").fetchall())
            finally:c.close()
    def get_history_entry(self,adaptation_id):
        e=self.get_evaluation_by_id(adaptation_id)
        if e is None:return None
        with self._lock:
            c=self._connect()
            try:
                row=c.execute("SELECT payload_json FROM plan_revision_proposals WHERE adaptation_id=?",[adaptation_id]).fetchone(); p=None if row is None else self._codec.decode_proposal(row[0])
            finally:c.close()
        return AdaptationHistoryEntry(e,p,self.get_revision_for_adaptation(adaptation_id))


class AdaptationPersistenceCoordinator:
    """Persists precomputed artifacts in retry-safe resolvability order."""
    def __init__(self,audit_repository,plan_repository): self.audit=audit_repository; self.plans=plan_repository
    def persist_no_change(self,evaluation):
        if evaluation.status is not AdaptationEvaluationStatus.NO_CHANGE: raise ValueError("evaluation must be NO_CHANGE")
        self.audit.save_evaluation(evaluation)
    def persist_applied(self,evaluation,proposal,revised_plan,record):
        self.audit.save_evaluation(evaluation); self.audit.save_proposal(evaluation.adaptation_id,proposal)
        self.plans.append_revision(proposal.source_plan_version,revised_plan)
        persisted=self.plans.get_by_id_version(record.result_plan_id,record.result_plan_version)
        if persisted != revised_plan: raise AdaptationPersistenceConflictError("APPLIED result plan is unresolvable")
        self.audit.save_revision(record)
    def persist_rejected(self,evaluation,proposal,record):
        if record.status is not PlanRevisionStatus.REJECTED: raise ValueError("record must be REJECTED")
        self.audit.save_evaluation(evaluation); self.audit.save_proposal(evaluation.adaptation_id,proposal); self.audit.save_revision(record)


class AdaptationHistoryReader:
    """Builds resolvability-checked history entries across both canonical stores."""
    def __init__(self, audit_repository, plan_repository):
        self.audit=audit_repository; self.plans=plan_repository
    def get_entry(self, adaptation_id):
        entry=self.audit.get_history_entry(adaptation_id)
        if entry is None:return None
        revision=entry.revision
        if revision is not None and revision.status is PlanRevisionStatus.APPLIED:
            result=self.plans.get_by_id_version(revision.result_plan_id,revision.result_plan_version)
            if result is None:
                raise AdaptationPersistenceDataError("APPLIED revision result plan is unresolvable")
        return entry
