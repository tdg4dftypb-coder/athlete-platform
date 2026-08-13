"""Dry-run-first explicit continuation-specification import."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
import sys
from training_plan.bootstrap import parse_bootstrap_specification,TrainingPlanBootstrapSpecificationError
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
from training_plan.persistence.paths import get_default_training_plan_db_path
from training_plan.repository import TrainingPlanConflictError,TrainingPlanRepositoryError

def run_import(input_path,*,specification_id,version,target_horizon_days,extension_days,created_at,apply=False,training_plan_db_path=None):
    try:
        bootstrap=parse_bootstrap_specification(Path(input_path).read_text())
        value=bootstrap.build_continuation_specification(specification_id=specification_id,version=version,
            target_horizon_days=target_horizon_days,extension_days=extension_days,created_at=created_at)
        print(f"Mode          : {'APPLY' if apply else 'DRY RUN'}")
        print(f"Plan ID       : {value.plan_id}\nSpecification : {value.specification_id}/v{value.version}")
        print(f"Target horizon: {value.target_horizon_days}\nExtension days: {value.extension_days}\nFingerprint   : {value.semantic_fingerprint}")
        if apply:DuckDbTrainingPlanRepository(get_default_training_plan_db_path(training_plan_db_path)).save_continuation_specification(value)
        return 0
    except (OSError,ValueError,TypeError,TrainingPlanBootstrapSpecificationError) as error:print(f"Continuation import error: {error}",file=sys.stderr);return 2
    except (TrainingPlanConflictError,TrainingPlanRepositoryError) as error:print(f"Continuation import conflict: {error}",file=sys.stderr);return 1

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True,type=Path);p.add_argument("--specification-id",required=True)
    p.add_argument("--version",required=True,type=int);p.add_argument("--target-horizon-days",required=True,type=int);p.add_argument("--extension-days",required=True,type=int)
    p.add_argument("--created-at",required=True);p.add_argument("--apply",action="store_true");p.add_argument("--training-plan-db",type=Path)
    a=p.parse_args(); created=datetime.fromisoformat(a.created_at.replace("Z","+00:00"))
    if created.utcoffset()!=timezone.utc.utcoffset(created):raise SystemExit("--created-at must be UTC")
    return run_import(a.input,specification_id=a.specification_id,version=a.version,target_horizon_days=a.target_horizon_days,extension_days=a.extension_days,
                      created_at=created,apply=a.apply,training_plan_db_path=a.training_plan_db)
if __name__=="__main__":raise SystemExit(main())
