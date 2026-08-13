"""Dry-run-first native continuation-specification import."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from training_plan.continuation_input import (
    TrainingPlanContinuationInputError,
    parse_continuation_specification,
)
from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
from training_plan.persistence.paths import get_default_training_plan_db_path
from training_plan.repository import TrainingPlanConflictError, TrainingPlanRepositoryError


def run_import(input_path, *, apply=False, training_plan_db_path=None):
    try:
        value = parse_continuation_specification(
            Path(input_path).read_text(encoding="utf-8")
        )
        _print_preview(value, apply)
        if apply:
            inserted = DuckDbTrainingPlanRepository(
                get_default_training_plan_db_path(training_plan_db_path)
            ).save_continuation_specification(value)
            print(f"Result        : {'persisted' if inserted else 'identical no-op'}")
        else:
            print("Result        : validation only; database unchanged")
        return 0
    except (OSError, TrainingPlanContinuationInputError) as error:
        print(f"Continuation import error: {error}", file=sys.stderr)
        return 2
    except (TrainingPlanConflictError, TrainingPlanRepositoryError) as error:
        print(f"Continuation import conflict: {error}", file=sys.stderr)
        return 1


def _print_preview(value, apply):
    print("Training Plan Continuation Specification")
    print(f"Mode          : {'APPLY' if apply else 'DRY RUN'}")
    print(f"Plan ID       : {value.plan_id}")
    print(f"Specification : {value.specification_id}")
    print(f"Version       : {value.version}")
    print(f"Target horizon: {value.target_horizon_days}")
    print(f"Extension days: {value.extension_days}")
    print(f"Created at    : {value.created_at.isoformat()}")
    print(f"Fingerprint   : {value.semantic_fingerprint}")
    print("Weekdays")
    for weekday in value.weekdays:
        for slot in weekday.slots:
            print(
                f"{weekday.weekday.name} | {slot.kind.value} | {slot.slot_id} | "
                f"{slot.session_type or '-'} | {slot.duration_minutes} | "
                f"{slot.target_tss if slot.target_tss is not None else '-'} | "
                f"{slot.intensity or '-'} | {slot.priority}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Validate or persist a native Training Plan continuation specification"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--training-plan-db", type=Path)
    arguments = parser.parse_args()
    return run_import(
        arguments.input,
        apply=arguments.apply,
        training_plan_db_path=arguments.training_plan_db,
    )


if __name__ == "__main__":
    raise SystemExit(main())
