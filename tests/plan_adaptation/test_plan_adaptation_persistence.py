from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from plan_adaptation import (
    AdaptationAction, AdaptationContextWindow, AdaptationEvaluationStatus,
    AdaptationHistoryReader, AdaptationPersistenceConflictError,
    AdaptationPersistenceCoordinator, AdaptationPersistenceDataError,
    AdaptationReasonCode, AdaptationWarningCode, AdaptationWindow,
    DuckDbPlanAdaptationRepository, PlanAdaptationEvaluation,
    PlanRevisionProposalBuilder, PlanRevisionRecord, PlanRevisionStatus,
    SessionAdaptationChange, TrainingPlanRevisionService,
)
from plan_adaptation.revision import PlanRevisionValidationCode
from training_plan import PlannedSession, PlannedSessionKind, TrainingPlan
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
from training_plan.repository import TrainingPlanConflictError

D=date(2026,8,13); NOW=datetime(2026,8,13,8,tzinfo=timezone.utc); FP="sha256:"+"d"*64

def session(i,day,typ="RUNNING",duration=60,tss=50.0):
    return PlannedSession(i,day,PlannedSessionKind.TRAINING,typ,duration,tss,"MODERATE",3,("base",))
def plan(version=3, duration=60):
    ss=[session("run",D+timedelta(days=1),duration=duration)]
    ss += [session(f"s{x}",D+timedelta(days=x),"ENDURANCE") for x in range(2,8)]
    return TrainingPlan("p",D+timedelta(days=1),D+timedelta(days=7),version,NOW,tuple(ss))
def evaluation(status=AdaptationEvaluationStatus.CHANGE_PROPOSED, aid="a", at=NOW, target=42):
    changes=() if status is AdaptationEvaluationStatus.NO_CHANGE else (SessionAdaptationChange("run",D+timedelta(days=1),AdaptationAction.SHORTEN,(AdaptationReasonCode.RECOVERY_PROTECTION,),target),)
    return PlanAdaptationEvaluation(aid,"1.0",status,D,AdaptationContextWindow.canonical(D),AdaptationWindow.canonical(D),"p",3,changes,
        (AdaptationReasonCode.RECOVERY_PROTECTION,) if changes else (),
        (AdaptationWarningCode.RECONCILIATION_UNAVAILABLE,),FP,at)
def artifacts():
    e=evaluation(); p=PlanRevisionProposalBuilder().build(e); src=plan(); result=TrainingPlanRevisionService().apply(p,src,generated_at=NOW+timedelta(hours=1)); r=PlanRevisionRecord.applied(p,e.adaptation_id,result,NOW+timedelta(hours=1)); return e,p,src,result,r

def test_round_trips_no_change_change_proposal_applied_and_rejected(tmp_path):
    repo=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb")
    no=evaluation(AdaptationEvaluationStatus.NO_CHANGE,"no")
    assert repo.save_evaluation(no) is True and repo.save_evaluation(no) is False
    assert repo.get_evaluation_by_id("no")==no
    e,p,_,result,r=artifacts()
    assert repo.save_evaluation(e) and repo.save_proposal(e.adaptation_id,p) and repo.save_revision(r)
    assert repo.get_evaluation_by_id(e.adaptation_id)==e
    assert repo.get_proposal_by_id(p.proposal_id)==p and repo.get_revision_by_id(r.revision_id)==r
    p2=replace(p,proposal_id="p2")
    rejected=PlanRevisionRecord.rejected(p2,"other",PlanRevisionValidationCode.UNKNOWN_SESSION,NOW)
    assert repo.save_evaluation(replace(e,adaptation_id="other"))
    assert repo.save_proposal("other",p2) and repo.save_revision(rejected)
    assert repo.get_revision_by_id(rejected.revision_id).status is PlanRevisionStatus.REJECTED

def test_collision_and_deterministic_history_latest(tmp_path):
    repo=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb")
    first=evaluation(AdaptationEvaluationStatus.NO_CHANGE,"same",NOW)
    repo.save_evaluation(first)
    with pytest.raises(AdaptationPersistenceConflictError): repo.save_evaluation(replace(first,policy_version="2.0"))
    later=replace(first,adaptation_id="later",evaluated_at=NOW+timedelta(hours=1))
    tomorrow=replace(first,adaptation_id="tomorrow",evaluation_date=D+timedelta(days=1),
        context_window=AdaptationContextWindow.canonical(D+timedelta(days=1)),mutation_window=AdaptationWindow.canonical(D+timedelta(days=1)))
    repo.save_evaluation(later); repo.save_evaluation(tomorrow)
    assert repo.get_evaluation_history()==(first,later,tomorrow)
    assert repo.get_latest_evaluation()==tomorrow
    assert repo.get_latest_evaluation_for_date(D)==later

def test_audit_timestamp_only_retries_are_idempotent_and_keep_first_timestamp(tmp_path):
    repo=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb"); e,p,_,result,r=artifacts()
    assert repo.save_evaluation(e) and repo.save_evaluation(replace(e,evaluated_at=NOW+timedelta(hours=2))) is False
    assert repo.get_evaluation_by_id(e.adaptation_id).evaluated_at==NOW
    assert repo.save_proposal(e.adaptation_id,p)
    assert repo.save_proposal(e.adaptation_id,replace(p,evaluated_at=NOW+timedelta(hours=2))) is False
    assert repo.get_proposal_by_id(p.proposal_id).evaluated_at==NOW
    assert repo.save_revision(r)
    assert repo.save_revision(replace(r,applied_at=NOW+timedelta(hours=3))) is False
    assert repo.get_revision_by_id(r.revision_id).applied_at==r.applied_at

def test_semantic_collisions_still_fail_for_all_record_types(tmp_path):
    repo=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb"); e,p,_,result,r=artifacts()
    repo.save_evaluation(e); repo.save_proposal(e.adaptation_id,p); repo.save_revision(r)
    with pytest.raises(AdaptationPersistenceConflictError): repo.save_evaluation(replace(e,policy_version="2.0"))
    with pytest.raises(AdaptationPersistenceConflictError): repo.save_proposal(e.adaptation_id,replace(p,source_plan_version=2))
    with pytest.raises(AdaptationPersistenceConflictError): repo.save_revision(replace(r,result_plan_version=5))

def test_no_change_coordinator_has_no_proposal_revision_or_new_plan(tmp_path):
    audit=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb"); plans=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb"); plans.save(plan())
    no=evaluation(AdaptationEvaluationStatus.NO_CHANGE,"no")
    AdaptationPersistenceCoordinator(audit,plans).persist_no_change(no)
    entry=audit.get_history_entry("no")
    assert entry.proposal is None and entry.revision is None and plans.get_by_id("p").version==3

def test_applied_path_resolves_both_versions_multisport_and_retry(tmp_path):
    audit=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb"); plans=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb")
    e,p,src,result,r=artifacts(); plans.save(src); coordinator=AdaptationPersistenceCoordinator(audit,plans)
    coordinator.persist_applied(e,p,result,r)
    assert plans.get_by_id_version("p",3)==src and plans.get_by_id_version("p",4)==result
    assert plans.get_by_id("p").sessions[0].session_type=="RUNNING"
    assert audit.get_history_entry(e.adaptation_id).revision==r
    assert AdaptationHistoryReader(audit,plans).get_entry(e.adaptation_id).revision==r
    coordinator.persist_applied(e,p,result,r)
    assert tuple(x.version for x in plans.list_records())==(3,4)

def test_history_reader_rejects_unresolvable_applied_corruption(tmp_path):
    audit=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb"); plans=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb")
    e,p,src,result,r=artifacts(); audit.save_evaluation(e); audit.save_proposal(e.adaptation_id,p); audit.save_revision(r)
    with pytest.raises(AdaptationPersistenceDataError,match="unresolvable"):
        AdaptationHistoryReader(audit,plans).get_entry(e.adaptation_id)

def test_partial_retry_and_competing_revision_conflict(tmp_path):
    audit=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb"); plans=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb")
    e,p,src,result,r=artifacts(); plans.save(src); plans.append_revision(3,result)
    AdaptationPersistenceCoordinator(audit,plans).persist_applied(e,p,result,r)
    assert audit.get_revision_by_id(r.revision_id)==r and plans.get_by_id("p").version==4
    competing=replace(result,sessions=(replace(result.sessions[0],duration_minutes=30),*result.sessions[1:]))
    with pytest.raises(TrainingPlanConflictError): plans.append_revision(3,competing)
    assert plans.get_by_id_version("p",4)==result

def test_rejected_path_is_auditable_without_result_plan(tmp_path):
    audit=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb"); plans=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb")
    e,p,src,_,_=artifacts(); plans.save(src)
    record=PlanRevisionRecord.rejected(p,e.adaptation_id,PlanRevisionValidationCode.UNKNOWN_SESSION,NOW)
    AdaptationPersistenceCoordinator(audit,plans).persist_rejected(e,p,record)
    assert audit.get_history_entry(e.adaptation_id).revision.failure_code is PlanRevisionValidationCode.UNKNOWN_SESSION
    assert plans.get_by_id("p").version==3

def test_training_plan_stream_unifies_base_revision_latest_and_cross_table_duplicate(tmp_path):
    plans=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb"); src=plan(); plans.save(src)
    e,p,_,result,r=artifacts(); assert plans.append_revision(3,result) is True
    assert plans.get_by_id("p")==result
    assert plans.get_by_id_version("p",3)==src and plans.get_by_id_version("p",4)==result
    assert tuple(x.version for x in plans.list_records())==(3,4)
    base4repo=DuckDbTrainingPlanRepository(tmp_path/"base4.duckdb"); base4repo.save(result)
    assert base4repo.append_revision(3,result) is False
    conflicting=replace(result,sessions=(replace(result.sessions[0],duration_minutes=30),*result.sessions[1:]))
    with pytest.raises(TrainingPlanConflictError): base4repo.append_revision(3,conflicting)

def test_history_tie_is_ordered_by_adaptation_id_and_retry_does_not_move_latest(tmp_path):
    repo=DuckDbPlanAdaptationRepository(tmp_path/"a.duckdb")
    a=evaluation(AdaptationEvaluationStatus.NO_CHANGE,"a",NOW); z=replace(a,adaptation_id="z")
    repo.save_evaluation(z); repo.save_evaluation(a)
    assert repo.get_evaluation_history()==(a,z) and repo.get_latest_evaluation()==z
    repo.save_evaluation(replace(a,evaluated_at=NOW+timedelta(days=1)))
    assert repo.get_latest_evaluation()==z

def test_multi_session_sibling_and_running_round_trip(tmp_path):
    plans=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb")
    src=plan(); swim=session("swim",D+timedelta(days=1),"SWIM",45,30.0)
    src=replace(src,sessions=(*src.sessions,swim)); plans.save(src)
    result=replace(src,version=4,generated_at=NOW+timedelta(hours=1),sessions=(replace(src.sessions[0],duration_minutes=42,target_tss=35.0),*src.sessions[1:]))
    plans.append_revision(3,result); loaded=plans.get_by_id_version("p",4)
    assert next(x for x in loaded.sessions if x.session_id=="run").session_type=="RUNNING"
    assert next(x for x in loaded.sessions if x.session_id=="swim")==swim
