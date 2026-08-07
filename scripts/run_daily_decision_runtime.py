"""CLI entry point for Automated Daily Decision Runtime execution."""
import argparse
from pathlib import Path
import sys
from typing import Optional, Union

from application.adaptive_daily_coordinator import AdaptiveDailyRuntimeOutcome
from application.adaptive_daily_production_composition import (
    create_production_adaptive_daily_runtime,
)


def run_daily_decision_runtime(
    health_db_path: Optional[Union[str, Path]] = None,
    biomarkers_db_path: Optional[Union[str, Path]] = None,
    decisions_db_path: Optional[Union[str, Path]] = None,
    training_plan_db_path: Optional[Union[str, Path]] = None,
    timezone_name: str = "Europe/Warsaw",
    coordinator=None,
) -> int:
    """CLI runner function for Automated Daily Decision Runtime.

    Returns exit code 0 for normal outcomes (EXECUTED, SKIPPED_ALREADY_COMPLETED,
    SKIPPED_IN_PROGRESS, RECOVERED_COMPLETED), and exit code 1 for FAILED, MISSING_PLAN,
    or unexpected error.
    """
    # 1. If explicit coordinator is injected (for unit testing CLI mechanics), use it directly
    if coordinator is not None:
        try:
            if hasattr(coordinator, "run_adaptive_daily") and not hasattr(coordinator, "run_daily_if_needed"):
                res = coordinator.run_adaptive_daily()
            elif hasattr(coordinator, "run_daily_if_needed"):
                res = coordinator.run_daily_if_needed()
            else:
                res = coordinator.run_adaptive_daily()
            _print_operational_output(res)
            val = res.outcome.value if hasattr(res.outcome, "value") else str(res.outcome)
            if val in ("failed", "missing_plan"):
                return 1
            return 0
        except Exception as err:
            print(f"Daily Decision Runtime Error: {type(err).__name__}", file=sys.stderr)
            return 1

    # 2. Production path: instantiate via create_production_adaptive_daily_runtime
    try:
        with create_production_adaptive_daily_runtime(
            health_db_path=health_db_path,
            biomarkers_db_path=biomarkers_db_path,
            decisions_db_path=decisions_db_path,
            training_plan_db_path=training_plan_db_path,
            timezone_name=timezone_name,
        ) as container:
            res = container.coordinator.run_adaptive_daily()
            _print_operational_output(res)
            val = res.outcome.value if hasattr(res.outcome, "value") else str(res.outcome)
            if val in ("failed", "missing_plan"):
                return 1
            return 0
    except Exception as err:
        print(f"Daily Decision Runtime Error: {type(err).__name__}", file=sys.stderr)
        return 1


def _print_operational_output(res) -> None:
    """Prints concise, privacy-safe operational metadata without health/medical data."""
    print("Daily Decision Runtime")
    run_date = getattr(res, "run_date_str", None)
    if run_date is not None:
        print(f"Run date    : {run_date}")

    val = res.outcome.value if hasattr(res.outcome, "value") else str(res.outcome)
    print(f"Outcome     : {val}")

    decision_id = getattr(res, "decision_id", None)
    if decision_id:
        print(f"Decision ID : {decision_id}")

    prescription_id = getattr(res, "prescription_id", None)
    if prescription_id:
        print(f"Prescription ID: {prescription_id}")

    rec = getattr(res, "record", None)
    if rec and getattr(rec, "attempt_count", None) is not None:
        print(f"Attempt     : {rec.attempt_count}")
    if rec and getattr(rec, "error_message", None):
        print(f"Error       : {rec.error_message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated Daily Decision Runtime Entry Point")
    parser.add_argument("--timezone", default="Europe/Warsaw", help="Local timezone name (default: Europe/Warsaw)")
    parser.add_argument("--decisions-db", default=None, help="Path to decisions DuckDB database")
    parser.add_argument("--health-db", default=None, help="Path to health DuckDB database")
    parser.add_argument("--biomarkers-db", default=None, help="Path to biomarkers DuckDB database")
    parser.add_argument("--training-plan-db", default=None, help="Path to training_plan DuckDB database")

    args = parser.parse_args()

    return run_daily_decision_runtime(
        health_db_path=args.health_db,
        biomarkers_db_path=args.biomarkers_db,
        decisions_db_path=args.decisions_db,
        training_plan_db_path=args.training_plan_db,
        timezone_name=args.timezone,
    )


if __name__ == "__main__":
    sys.exit(main())
