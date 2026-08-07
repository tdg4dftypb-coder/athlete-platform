"""CLI entry point for Automated Daily Decision Runtime execution."""
import argparse
from pathlib import Path
import sys
from typing import Optional, Union

from decision.daily_execution import DailyCoordinatorOutcome
from decision.daily_production_composition import create_production_daily_decision_runtime


def run_daily_decision_runtime(
    health_db_path: Optional[Union[str, Path]] = None,
    biomarkers_db_path: Optional[Union[str, Path]] = None,
    decisions_db_path: Optional[Union[str, Path]] = None,
    timezone_name: str = "Europe/Warsaw",
    coordinator=None,
) -> int:
    """CLI runner function for Automated Daily Decision Runtime.

    Returns exit code 0 for normal outcomes (EXECUTED, SKIPPED_ALREADY_COMPLETED,
    SKIPPED_IN_PROGRESS, RECOVERED_COMPLETED), and exit code 1 for FAILED or unexpected error.
    """
    # 1. If explicit coordinator is injected (for unit testing CLI mechanics), use it directly
    if coordinator is not None:
        try:
            res = coordinator.run_daily_if_needed()
            _print_operational_output(res)
            if res.outcome == DailyCoordinatorOutcome.FAILED:
                return 1
            return 0
        except Exception as err:
            print(f"Daily Decision Runtime Error: {type(err).__name__}", file=sys.stderr)
            return 1

    # 2. Production path: instantiate via create_production_daily_decision_runtime
    try:
        with create_production_daily_decision_runtime(
            health_db_path=health_db_path,
            biomarkers_db_path=biomarkers_db_path,
            decisions_db_path=decisions_db_path,
            timezone_name=timezone_name,
        ) as container:
            res = container.coordinator.run_daily_if_needed()
            _print_operational_output(res)
            if res.outcome == DailyCoordinatorOutcome.FAILED:
                return 1
            return 0
    except Exception as err:
        print(f"Daily Decision Runtime Error: {type(err).__name__}", file=sys.stderr)
        return 1


def _print_operational_output(res) -> None:
    """Prints concise, privacy-safe operational metadata without health/medical data."""
    print("Daily Decision Runtime")
    print(f"Run date    : {res.run_date_str}")
    print(f"Outcome     : {res.outcome.value}")
    if res.decision_id:
        print(f"Decision ID : {res.decision_id}")
    if res.record and res.record.attempt_count is not None:
        print(f"Attempt     : {res.record.attempt_count}")
    if res.record and res.record.error_message:
        print(f"Error       : {res.record.error_message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated Daily Decision Runtime Entry Point")
    parser.add_argument("--timezone", default="Europe/Warsaw", help="Local timezone name (default: Europe/Warsaw)")
    parser.add_argument("--decisions-db", default=None, help="Path to decisions DuckDB database")
    parser.add_argument("--health-db", default=None, help="Path to health DuckDB database")
    parser.add_argument("--biomarkers-db", default=None, help="Path to biomarkers DuckDB database")

    args = parser.parse_args()

    return run_daily_decision_runtime(
        health_db_path=args.health_db,
        biomarkers_db_path=args.biomarkers_db,
        decisions_db_path=args.decisions_db,
        timezone_name=args.timezone,
    )


if __name__ == "__main__":
    sys.exit(main())
