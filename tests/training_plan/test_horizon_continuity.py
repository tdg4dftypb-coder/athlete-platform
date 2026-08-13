from dataclasses import replace
from datetime import date,datetime,timedelta,timezone
import pytest

from plan_adaptation.builder import AdaptationContextBuilder
from plan_adaptation.policy import DeterministicAdaptationPolicy
from plan_adaptation.revision import PlanRevisionProposalBuilder,TrainingPlanRevisionService
from application.athlete_assessment import AthleteAssessment,AthleteAssessmentReason,AthleteAssessmentStatus,FatigueStatus
from application.training_assessment import TrainingAssessment,TrainingAssessmentStatus
from training_plan import *
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
from training_plan.repository import TrainingPlanConflictError
from training_plan.repository import TrainingPlanDataError
import duckdb

NOW=datetime(2026,9,2,6,tzinfo=timezone.utc); D=date(2026,9,2)

def slot(id,kind=PlannedSessionKind.TRAINING,type="ENDURANCE",duration=60):
    return ContinuationSessionSlot(id,kind,None if kind is PlannedSessionKind.REST else type,
        0 if kind is PlannedSessionKind.REST else duration,0.0 if kind is PlannedSessionKind.REST else 50.0,
        None if kind is PlannedSessionKind.REST else "MODERATE",1 if kind is PlannedSessionKind.REST else 3,("continuity",))

def spec(plan_id="plan-a",target_horizon_days=28,extension_days=28,created=NOW):
    weekdays=[]
    for day in Weekday:
        values=(slot("rest",PlannedSessionKind.REST),) if day is Weekday.MONDAY else (slot("main","RUNNING" if False else PlannedSessionKind.TRAINING,"RUNNING" if day is Weekday.TUESDAY else "ENDURANCE"),)
        if day is Weekday.SUNDAY: values=(slot("endurance"),slot("swim",type="SWIM",duration=40))
        weekdays.append(ContinuationWeekday(day,values))
    return TrainingPlanContinuationSpecification.create("continuation-a",1,plan_id,target_horizon_days,extension_days,tuple(weekdays),created)

def source(end=date(2026,9,6),version=3,short=False):
    sessions=[]; day=date(2026,8,10)
    while day<=end:
        sessions.append(PlannedSession(f"old:{day}",day,PlannedSessionKind.TRAINING,"ENDURANCE",42 if short and day==date(2026,9,3) else 60,50.0,"MODERATE",3,("old",)))
        day+=timedelta(days=1)
    return TrainingPlan("plan-a",date(2026,8,10),end,version,NOW,tuple(sessions))

def test_specification_roundtrip_multisession_open_type_idempotency_and_collision(tmp_path):
    repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb"); value=spec()
    assert repo.save_continuation_specification(value) is True
    assert repo.save_continuation_specification(replace(value,created_at=NOW+timedelta(hours=1))) is False
    assert repo.get_continuation_specification(value.specification_id,1)==value
    assert repo.get_latest_continuation_specification_for_plan("plan-a")==value
    sunday=value.weekdays[Weekday.SUNDAY.value]; assert len(sunday.slots)==2
    assert value.weekdays[Weekday.TUESDAY.value].slots[0].session_type=="RUNNING"
    changed=TrainingPlanContinuationSpecification.create(value.specification_id,value.version,value.plan_id,42,28,value.weekdays,NOW)
    with pytest.raises(TrainingPlanConflictError): repo.save_continuation_specification(changed)

def test_sufficient_coverage_is_noop():
    result=TrainingPlanHorizonExtensionService().extend(source(date(2026,9,20)),spec(),date(2026,9,9),generated_at=NOW)
    assert result.status is HorizonExtensionStatus.NO_EXTENSION and result.plan.version==3

def test_boundary_extends_full_chunk_preserves_old_adaptation_and_builds_context():
    old=source(short=True); result=TrainingPlanHorizonExtensionService().extend(old,spec(),date(2026,9,9),generated_at=NOW)
    plan=result.plan
    assert result.status is HorizonExtensionStatus.EXTENDED
    assert (plan.plan_id,plan.version,plan.start_date,plan.end_date)==("plan-a",4,date(2026,8,10),date(2026,10,4))
    assert plan.sessions[:len(old.sessions)]==old.sessions
    assert next(x for x in plan.sessions if x.session_id=="old:2026-09-03").duration_minutes==42
    context=AdaptationContextBuilder().build(evaluation_date=D,source_plan=plan,
        historical_planned_sessions=tuple(x for x in plan.sessions if D-timedelta(days=7)<=x.date<=D),
        reconciliations=(),training_load=None,athlete_state=None,constraints=None,weekly_rhythm=None,built_at=NOW)
    assert context.mutation_window.mutation_end==date(2026,9,9)
    assert {x.date for x in context.future_sessions}=={D+timedelta(days=n) for n in range(1,8)}

def test_new_ids_deterministic_multisession_unique_and_no_rest_mix():
    service=TrainingPlanHorizonExtensionService(); a=service.extend(source(),spec(),date(2026,9,9),generated_at=NOW).plan
    b=service.extend(source(),spec(),date(2026,9,9),generated_at=NOW+timedelta(hours=1)).plan
    newa=[x for x in a.sessions if x.date>date(2026,9,6)]; newb=[x for x in b.sessions if x.date>date(2026,9,6)]
    assert [x.session_id for x in newa]==[x.session_id for x in newb]
    sunday=[x for x in newa if x.date.weekday()==6]; assert {x.session_type for x in sunday}=={"ENDURANCE","SWIM"}
    assert len({x.session_id for x in newa})==len(newa)

def test_extension_persistence_retry_and_competing_revision(tmp_path):
    repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb"); old=source(); repo.save(old)
    extended=TrainingPlanHorizonExtensionService().extend(old,spec(),date(2026,9,9),generated_at=NOW).plan
    assert repo.append_revision(3,extended) is True and repo.append_revision(3,extended) is False
    assert repo.get_by_id_version("plan-a",3)==old and repo.get_by_id("plan-a")==extended
    with pytest.raises(TrainingPlanConflictError): repo.append_revision(3,replace(extended,end_date=date(2026,10,5),sessions=extended.sessions+(PlannedSession("extra",date(2026,10,5),PlannedSessionKind.REST,None,0,0.0,None,1,("x",)),)))

def test_spec_rejects_rest_training_mix():
    with pytest.raises(ValueError,match="REST"):
        ContinuationWeekday(Weekday.MONDAY,(slot("rest",PlannedSessionKind.REST),slot("run",type="RUNNING")))


def test_specification_requires_aware_utc_audit_time_and_seven_unique_days():
    with pytest.raises(ValueError,match="UTC"):
        TrainingPlanContinuationSpecification.create("x",1,"plan-a",28,28,spec().weekdays,datetime(2026,9,2))
    with pytest.raises(ValueError,match="seven"):
        TrainingPlanContinuationSpecification.create("x",1,"plan-a",28,28,spec().weekdays[:-1],NOW)


def test_persisted_unknown_schema_is_corruption(tmp_path):
    path=tmp_path/"p.duckdb";repo=DuckDbTrainingPlanRepository(path);repo.save_continuation_specification(spec())
    connection=duckdb.connect(str(path));connection.execute(
        "UPDATE training_plan_continuation_specifications SET payload_json=replace(payload_json, '\"schema_version\":\"1.0\"', '\"schema_version\":\"9.0\"')")
    connection.close()
    with pytest.raises(TrainingPlanDataError):repo.get_latest_continuation_specification_for_plan("plan-a")


def test_explicit_logical_plan_transition_is_not_auto_joined():
    with pytest.raises(ValueError,match="different plan"):
        TrainingPlanHorizonExtensionService().extend(source(),spec("plan-b"),date(2026,9,9),generated_at=NOW)


def test_continuity_v4_then_adaptation_consumes_v4_and_produces_v5(tmp_path):
    repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");old=source();repo.save(old)
    extended=TrainingPlanHorizonExtensionService().extend(old,spec(),date(2026,9,9),generated_at=NOW).plan
    repo.append_revision(3,extended)
    training=TrainingAssessment(NOW,None,TrainingAssessmentStatus.NO_CLEAR_PATTERN,())
    caution=AthleteAssessment(NOW,AthleteAssessmentStatus.CAUTION,training,(AthleteAssessmentReason.LOW_RECOVERY,),FatigueStatus.NORMAL)
    context=AdaptationContextBuilder().build(evaluation_date=D,source_plan=repo.get_by_id("plan-a"),
        historical_planned_sessions=tuple(x for x in extended.sessions if D-timedelta(days=7)<=x.date<=D),
        reconciliations=(),training_load=None,athlete_state=caution,constraints=None,weekly_rhythm=None,built_at=NOW)
    evaluation=DeterministicAdaptationPolicy().evaluate(context,evaluated_at=NOW)
    proposal=PlanRevisionProposalBuilder().build(evaluation)
    adapted=TrainingPlanRevisionService().apply(proposal,extended,generated_at=NOW+timedelta(minutes=1))
    assert proposal.source_plan_version==4 and adapted.version==5
    repo.append_revision(4,adapted);assert repo.get_by_id("plan-a").version==5


def test_specification_v2_changes_only_dates_of_next_future_extension():
    service=TrainingPlanHorizonExtensionService();v1=service.extend(source(),spec(),date(2026,9,9),generated_at=NOW).plan
    v2spec=TrainingPlanContinuationSpecification.create("continuation-a",2,"plan-a",28,28,spec().weekdays,NOW+timedelta(days=1))
    v2=service.extend(v1,v2spec,date(2026,10,6),generated_at=NOW+timedelta(days=1)).plan
    assert v2.sessions[:len(v1.sessions)]==v1.sessions
    newly_generated=v2.sessions[len(v1.sessions):]
    assert newly_generated and all(":2:" in item.session_id for item in newly_generated)
    assert not ({item.session_id for item in v1.sessions}&{item.session_id for item in newly_generated})


def test_target_horizon_is_fingerprinted_and_independent_from_extension_chunk():
    short_chunks=spec(target_horizon_days=42,extension_days=14)
    default=spec()
    assert short_chunks.target_horizon_days==42 and short_chunks.extension_days==14
    assert short_chunks.semantic_fingerprint!=default.semantic_fingerprint
    result=TrainingPlanHorizonExtensionService().extend(
        source(),short_chunks,D+timedelta(days=42),generated_at=NOW).plan
    assert result.end_date>=D+timedelta(days=42)
    assert (result.end_date-date(2026,9,6)).days%14==0


@pytest.mark.parametrize("target",(date(2026,9,3),date(2026,9,7),date(2026,10,1)))
def test_plan_by_date_resolves_latest_extended_version(tmp_path,target):
    repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");old=source();repo.save(old)
    extended=TrainingPlanHorizonExtensionService().extend(old,spec(),date(2026,9,9),generated_at=NOW).plan
    repo.append_revision(3,extended)
    assert repo.get_by_id("plan-a")==extended
    assert repo.get_by_id_version("plan-a",3)==old
    assert repo.get_by_id_version("plan-a",4)==extended
    assert repo.get_for_date(target)==extended
