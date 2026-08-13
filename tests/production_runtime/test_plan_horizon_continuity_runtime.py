from datetime import date,datetime,timedelta,timezone
from types import SimpleNamespace
import pytest
from production_runtime.horizon_continuity import PlanHorizonContinuityAdapter,CONTINUATION_SPECIFICATION_UNAVAILABLE
from production_runtime.coordinator import RuntimePhaseError
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
from tests.training_plan.test_horizon_continuity import source,spec

NOW=datetime(2026,9,2,6,tzinfo=timezone.utc); D=date(2026,9,2)
class Clock:
 def now_utc(self):return NOW
def context():return SimpleNamespace(target_local_date=D,result=SimpleNamespace(training_plan_id="plan-a"))

def test_runtime_sufficient_coverage_noop(tmp_path):
 repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");repo.save(source(date(2026,10,4)));repo.save_continuation_specification(spec())
 result=PlanHorizonContinuityAdapter(repo,Clock()).execute(context())
 assert not result.changed_state and repo.get_by_id("plan-a").version==3

@pytest.mark.parametrize("target,expected_target",((date(2026,8,13),date(2026,9,10)),(date(2026,8,14),date(2026,9,11))))
def test_current_production_dates_trigger_proactive_28_day_extension(tmp_path,target,expected_target):
 repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");repo.save(source());repo.save_continuation_specification(spec())
 ctx=SimpleNamespace(target_local_date=target,result=SimpleNamespace(training_plan_id="plan-a"))
 result=PlanHorizonContinuityAdapter(repo,Clock()).execute(ctx)
 assert expected_target>date(2026,9,6) and result.changed_state
 assert repo.get_by_id("plan-a").end_date==date(2026,10,4)

def test_runtime_missing_specification_fails_operator_visible(tmp_path):
 repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");repo.save(source())
 with pytest.raises(RuntimePhaseError) as error:PlanHorizonContinuityAdapter(repo,Clock()).execute(context())
 assert error.value.code==CONTINUATION_SPECIFICATION_UNAVAILABLE

def test_runtime_extension_retry_and_recovery_after_plan_write(tmp_path):
 repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");repo.save(source());repo.save_continuation_specification(spec())
 adapter=PlanHorizonContinuityAdapter(repo,Clock());first=adapter.execute(context());second=adapter.execute(context())
 assert first.changed_state and not second.changed_state
 assert repo.get_by_id("plan-a").version==4 and first.artifact_ids==second.artifact_ids

def test_continuity_then_adaptation_can_use_latest_single_plan(tmp_path):
 repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");repo.save(source());repo.save_continuation_specification(spec())
 PlanHorizonContinuityAdapter(repo,Clock()).execute(context()); latest=repo.get_for_date(D)
 assert latest.version==4 and latest.end_date>=D+timedelta(days=7)

def test_recovery_after_continuity_v4_and_adaptation_v5_does_not_create_v6(tmp_path):
 repo=DuckDbTrainingPlanRepository(tmp_path/"p.duckdb");base=source();repo.save(base);repo.save_continuation_specification(spec())
 adapter=PlanHorizonContinuityAdapter(repo,Clock());adapter.execute(context());v4=repo.get_by_id("plan-a")
 v5=__import__('dataclasses').replace(v4,version=5,generated_at=NOW+timedelta(minutes=1))
 repo.append_revision(4,v5)
 recovered=adapter.execute(context())
 assert not recovered.changed_state and recovered.artifact_ids==("training-plan:plan-a:v5",)
 assert repo.get_by_id("plan-a").version==5
