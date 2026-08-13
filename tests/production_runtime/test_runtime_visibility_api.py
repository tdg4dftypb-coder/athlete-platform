from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from plan_adaptation.models import AdaptationAction, AdaptationEvaluationStatus
from plan_adaptation.persistence import PlanRevisionStatus
from production_runtime.diagnostics import (
    RuntimeArtifactReferences, RuntimeCounterDiagnostic, RuntimeOperationalHealth,
    RuntimeOperationalSnapshot, RuntimePhaseDiagnostic, RuntimeResumability,
)
from production_runtime.models import PhaseStatus, RuntimePhase, RuntimeStatus
from production_runtime.models import ProductionDailyRuntimeResult, logical_execution_key
from production_runtime.persistence import DuckDbRuntimeAuditRepository
from production_runtime.diagnostics import RuntimeOperationalStatusReader
from production_runtime.visibility import (
    DuckDbPlanAdaptationEntryReader, ProductionRuntimeVisibilityReader,
)
from server.app import create_dashboard_wsgi_app
from training_plan import PlannedSession, PlannedSessionKind, TrainingPlan


NOW = datetime(2026, 8, 14, 0, 30, tzinfo=timezone.utc)


def plan(version, end):
    sessions=[];day=date(2026,8,10)
    while day<=end:
        sessions.append(PlannedSession(f"s{version}:{day}",day,PlannedSessionKind.REST,
                                       None,0,0.0,None,1,()))
        day+=timedelta(days=1)
    return TrainingPlan("plan-a",date(2026,8,10),end,version,NOW,tuple(sessions))


class Plans:
    def __init__(self, *values): self.values={(x.plan_id,x.version):x for x in values}
    def get_by_id_version(self, plan_id, version): return self.values.get((plan_id,version))
    def get_by_id(self, plan_id):
        values=[x for (pid,_),x in self.values.items() if pid==plan_id]
        return max(values,key=lambda x:x.version) if values else None


def phase(name, *, changed=False, artifacts=(), status=PhaseStatus.COMPLETED, codes=()):
    return RuntimePhaseDiagnostic(name, True, status, NOW, NOW, changed, None, artifacts, codes)


def snapshot(*present, status=RuntimeStatus.COMPLETED):
    by={item.phase:item for item in present}
    phases=tuple(by.get(name,RuntimePhaseDiagnostic(name,False)) for name in RuntimePhase)
    return RuntimeOperationalSnapshot(
        "runtime-latest", "2026-08-14:1.0", date(2026,8,14), "1.0", 12, status,
        RuntimeOperationalHealth.HEALTHY, NOW, NOW if status is not RuntimeStatus.RUNNING else None,
        NOW, False, RuntimeResumability.NO_ACTION, None, phases, None, (), (),
        RuntimeCounterDiagnostic(None,None,None,None),
        RuntimeArtifactReferences("decision-a","plan-a","rx-a",True),
    )


class RuntimeReader:
    def __init__(self, value): self.value=value
    def get_latest(self): return self.value


class Adaptations:
    def __init__(self, entry): self.entry=entry
    def get_entry(self, _key): return self.entry


def adaptation_entry(status, revision_status=None, *, result_exists=True):
    change=SimpleNamespace(action=AdaptationAction.SHORTEN)
    evaluation=SimpleNamespace(
        status=status, source_plan_id="plan-a", source_plan_version=2,
        proposed_changes=() if status is AdaptationEvaluationStatus.NO_CHANGE else (change,),
        reason_codes=(),
    )
    proposal=None if status is AdaptationEvaluationStatus.NO_CHANGE else SimpleNamespace()
    revision=None if revision_status is None else SimpleNamespace(
        status=revision_status, result_plan_id="plan-a" if result_exists else "missing-plan",
        result_plan_version=3, failure_code=(SimpleNamespace(value="invalid_revision")
                                             if revision_status is PlanRevisionStatus.REJECTED else None),
    )
    return evaluation,proposal,revision


def reader(runtime, adaptation=None, include_result=True):
    plans=[plan(1,date(2026,9,6)),plan(2,date(2026,10,4))]
    if include_result: plans.append(plan(3,date(2026,10,4)))
    return ProductionRuntimeVisibilityReader(RuntimeReader(runtime),Plans(*plans),Adaptations(adaptation) if adaptation else None)


def test_latest_modern_runtime_and_continuity_changed_transition():
    runtime=snapshot(
        phase(RuntimePhase.PLAN_PRESCRIPTION,artifacts=("plan-a","rx-a")),
        phase(RuntimePhase.PLAN_HORIZON_CONTINUITY,changed=True,artifacts=("training-plan:plan-a:v2",)),
        phase(RuntimePhase.PLAN_ADAPTATION),phase(RuntimePhase.MORNING_BRIEFING),phase(RuntimePhase.PUBLICATION),
    )
    payload=reader(runtime).get_latest_payload()["runtime"]
    continuity=payload["phases"]["plan_horizon_continuity"]["continuity"]
    assert payload["runtime_id"]=="runtime-latest" and payload["revision"]==12
    assert payload["plan"]=={"plan_id":"plan-a","version":2,"coverage_start":"2026-08-10","coverage_end":"2026-10-04"}
    assert continuity["source_plan_version"]==1 and continuity["result_plan_version"]==2
    assert continuity["source_coverage_end"]=="2026-09-06" and continuity["result_coverage_end"]=="2026-10-04"
    assert continuity["target_date"] is None and continuity["target_horizon_days"] is None


def test_continuity_completed_without_change_uses_same_plan():
    runtime=snapshot(phase(RuntimePhase.PLAN_HORIZON_CONTINUITY,artifacts=("training-plan:plan-a:v2",)))
    value=reader(runtime).get_latest_payload()["runtime"]["phases"]["plan_horizon_continuity"]
    assert value["status"]=="completed" and value["changed_state"] is False
    assert value["continuity"]["source_plan_version"]==value["continuity"]["result_plan_version"]==2


@pytest.mark.parametrize("evaluation_status,revision_status,outcome",(
    (AdaptationEvaluationStatus.NO_CHANGE,None,"NO_CHANGE"),
    (AdaptationEvaluationStatus.CHANGE_PROPOSED,PlanRevisionStatus.APPLIED,"APPLIED"),
    (AdaptationEvaluationStatus.CHANGE_PROPOSED,PlanRevisionStatus.REJECTED,"REJECTED"),
))
def test_adaptation_outcomes(evaluation_status,revision_status,outcome):
    entry=adaptation_entry(evaluation_status,revision_status)
    runtime=snapshot(phase(RuntimePhase.PLAN_ADAPTATION,changed=outcome=="APPLIED",artifacts=("adapt-a",)))
    value=reader(runtime,entry).get_latest_payload()["runtime"]["phases"]["plan_adaptation"]["adaptation"]
    assert value["outcome"]==outcome and value["source_plan_version"]==2
    assert value["actions"]==([] if outcome=="NO_CHANGE" else ["SHORTEN"])
    if outcome=="APPLIED": assert value["result_plan_version"]==3
    if outcome=="REJECTED": assert value["failure_code"]=="invalid_revision"


@pytest.mark.parametrize("missing",(RuntimePhase.PLAN_HORIZON_CONTINUITY,RuntimePhase.PLAN_ADAPTATION))
def test_historical_runtime_missing_newer_phase_is_available_false(missing):
    present=[phase(name) for name in (RuntimePhase.PLAN_PRESCRIPTION,RuntimePhase.PLAN_HORIZON_CONTINUITY,
                                      RuntimePhase.PLAN_ADAPTATION,RuntimePhase.MORNING_BRIEFING,RuntimePhase.PUBLICATION)
             if name is not missing]
    payload=reader(snapshot(*present)).get_latest_payload()["runtime"]
    assert payload["phases"][missing.value]=={"available":False}


def test_corrupt_adaptation_reference_is_bounded_unresolvable():
    runtime=snapshot(phase(RuntimePhase.PLAN_ADAPTATION,artifacts=("missing",)))
    value=reader(runtime).get_latest_payload()["runtime"]["phases"]["plan_adaptation"]["adaptation"]
    assert value["artifact_status"]=="unresolvable" and value["outcome"] is None


def test_applied_missing_result_plan_is_reported_unresolvable():
    entry=adaptation_entry(AdaptationEvaluationStatus.CHANGE_PROPOSED,PlanRevisionStatus.APPLIED,result_exists=False)
    runtime=snapshot(phase(RuntimePhase.PLAN_ADAPTATION,artifacts=("adapt-a",)))
    value=reader(runtime,entry,include_result=False).get_latest_payload()["runtime"]["phases"]["plan_adaptation"]["adaptation"]
    assert value["artifact_status"]=="unresolvable"


def test_applied_adaptation_result_is_attempt_related_plan_after_continuity():
    entry=adaptation_entry(AdaptationEvaluationStatus.CHANGE_PROPOSED,PlanRevisionStatus.APPLIED)
    runtime=snapshot(
        phase(RuntimePhase.PLAN_HORIZON_CONTINUITY,changed=True,artifacts=("training-plan:plan-a:v2",)),
        phase(RuntimePhase.PLAN_ADAPTATION,changed=True,artifacts=("adapt-a",)),
    )
    payload=reader(runtime,entry).get_latest_payload()["runtime"]
    assert payload["plan"]["version"]==3


def test_corrupt_adaptation_entry_does_not_break_related_plan_projection():
    class Corrupt:
        def get_entry(self, _key): raise ValueError("bad payload")
    runtime=snapshot(
        phase(RuntimePhase.PLAN_HORIZON_CONTINUITY,artifacts=("training-plan:plan-a:v2",)),
        phase(RuntimePhase.PLAN_ADAPTATION,artifacts=("adapt-a",)),
    )
    value=ProductionRuntimeVisibilityReader(RuntimeReader(runtime),Plans(plan(2,date(2026,10,4))),Corrupt())
    assert value.get_latest_payload()["runtime"]["plan"]["version"]==2


def test_missing_adaptation_database_does_not_create_file(tmp_path):
    path=tmp_path/"plan_adaptation.duckdb"
    source=DuckDbPlanAdaptationEntryReader(path)
    assert source.get_entry("missing") is None and not path.exists()


def request(app):
    response={}
    body=app({"PATH_INFO":"/api/v1/production-runtime/latest","REQUEST_METHOD":"GET"},
             lambda status,headers:response.update(status=status,headers=headers))
    response["json"]=json.loads(body[0]);return response


def test_http_endpoint_serializes_injected_latest_reader_without_side_effects(tmp_path):
    runtime=snapshot(phase(RuntimePhase.PLAN_HORIZON_CONTINUITY,artifacts=("training-plan:plan-a:v2",)))
    adaptation_path=tmp_path/"plan_adaptation.duckdb"
    app=create_dashboard_wsgi_app(production_runtime_visibility_reader=reader(runtime))
    response=request(app)
    assert response["status"]=="200 OK" and response["json"]["schema_version"]=="1.0"
    assert response["json"]["runtime"]["runtime_id"]=="runtime-latest"
    assert not adaptation_path.exists()


def test_empty_endpoint_is_legal_and_read_only():
    response=request(create_dashboard_wsgi_app())
    assert response["status"]=="200 OK"
    assert response["json"]=={"schema_version":"1.0","runtime":None}


def test_latest_ordering_uses_canonical_runtime_repository_contract(tmp_path):
    repository=DuckDbRuntimeAuditRepository(tmp_path/"runtime.duckdb")
    for runtime_id,started,target in (
        ("runtime-old",NOW-timedelta(hours=2),date(2026,8,13)),
        ("runtime-new",NOW-timedelta(hours=1),date(2026,8,14)),
    ):
        repository.append(ProductionDailyRuntimeResult(
            runtime_id,logical_execution_key(target),1,"1.0",target,"Europe/Warsaw",
            started,None,RuntimeStatus.RUNNING,
        ))
    clock=SimpleNamespace(now_utc=lambda:NOW)
    runtime_reader=RuntimeOperationalStatusReader(repository,clock=clock)
    payload=ProductionRuntimeVisibilityReader(runtime_reader,Plans(plan(1,date(2026,9,6)))).get_latest_payload()
    assert payload["runtime"]["runtime_id"]=="runtime-new"
