"""Dry-run-first operator command for persisting an initial baseline TrainingPlan."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from training_plan.bootstrap import (
    TrainingPlanBootstrapSpecificationError,
    parse_bootstrap_specification,
)
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
from training_plan.persistence.paths import get_default_training_plan_db_path
from training_plan.repository import TrainingPlanConflictError, TrainingPlanRepositoryError


def run_bootstrap_training_plan(
    input_path: str | Path,
    *,
    apply: bool = False,
    training_plan_db_path: str | Path | None = None,
) -> int:
    target = get_default_training_plan_db_path(training_plan_db_path)
    try:
        payload = Path(input_path).read_text(encoding="utf-8")
        specification = parse_bootstrap_specification(payload)
        plan = specification.build_plan()
        _print_preview(specification.intent.intent_id, plan, target, apply)
        if apply:
            DuckDbTrainingPlanRepository(target).save(plan)
            print("Result       : persisted (or identical no-op)")
        else:
            print("Result       : validation only; database unchanged")
        return 0
    except (OSError, TrainingPlanBootstrapSpecificationError) as error:
        print(f"Training Plan bootstrap error: {error}", file=sys.stderr)
        return 2
    except TrainingPlanConflictError as error:
        print(f"Training Plan bootstrap conflict: {error}", file=sys.stderr)
        return 1
    except TrainingPlanRepositoryError as error:
        print(f"Training Plan bootstrap persistence error: {error}", file=sys.stderr)
        return 1


def _print_preview(intent_id, plan, target, apply):
    print("Initial Training Plan Bootstrap")
    print(f"Mode          : {'APPLY' if apply else 'DRY RUN'}")
    print(f"Target DB     : {target}")
    print(f"Plan ID       : {plan.plan_id}")
    print(f"Intent ID     : {intent_id}")
    print(f"Start date    : {plan.start_date.isoformat()}")
    print(f"End date      : {plan.end_date.isoformat()}")
    print(f"Version       : {plan.version}")
    print(f"Generated at  : {plan.generated_at.isoformat()}")
    print(f"Supersedes    : {plan.supersedes_plan_id or '-'}")
    print("Sessions")
    for session in plan.sessions:
        print(
            f"{session.date.isoformat()} | {session.kind.value} | "
            f"{session.session_type or '-'} | {session.duration_minutes} | "
            f"{session.target_tss if session.target_tss is not None else '-'} | "
            f"{session.intensity or '-'} | {session.priority}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or persist an initial baseline Training Plan")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Persist after validation; default is dry run")
    parser.add_argument("--training-plan-db", type=Path)
    arguments = parser.parse_args()
    return run_bootstrap_training_plan(
        arguments.input,
        apply=arguments.apply,
        training_plan_db_path=arguments.training_plan_db,
    )


if __name__ == "__main__":
    raise SystemExit(main())
