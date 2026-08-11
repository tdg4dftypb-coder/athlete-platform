"""Production-candidate CLI for the authoritative daily runtime coordinator."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from production_runtime.clock import SystemUtcRuntimeClock, target_local_date_at
from production_runtime.models import PhaseStatus, RuntimeStatus


def run_production_daily_runtime(
    target_date: date | None = None,
    *,
    health_db_path: str | Path | None = None,
    biomarkers_db_path: str | Path | None = None,
    decisions_db_path: str | Path | None = None,
    training_plan_db_path: str | Path | None = None,
    runtime_audit_db_path: str | Path | None = None,
    fit_source_path: str | Path | None = None,
    coordinator=None,
    clock=None,
) -> int:
    runtime_clock = clock or SystemUtcRuntimeClock()
    resolved_date = target_date or target_local_date_at(runtime_clock.now_utc())
    try:
        if coordinator is None:
            from production_runtime.production_composition import create_production_daily_runtime
            with create_production_daily_runtime(
                health_db_path=health_db_path,
                biomarkers_db_path=biomarkers_db_path,
                decisions_db_path=decisions_db_path,
                training_plan_db_path=training_plan_db_path,
                runtime_audit_db_path=runtime_audit_db_path,
                fit_source_path=fit_source_path,
                clock=runtime_clock,
                target_local_date=resolved_date,
            ) as container:
                result = container.runtime.run_new_attempt(resolved_date)
        else:
            result = coordinator.run_new_attempt(resolved_date)
        _print_result(result)
        return 0 if result.status is RuntimeStatus.COMPLETED else 1
    except Exception as error:
        print(f"Production Daily Runtime Error: {type(error).__name__}", file=sys.stderr)
        return 1


def _print_result(result) -> None:
    print("Production Daily Runtime")
    print(f"Runtime ID   : {result.runtime_id}")
    print(f"Target date  : {result.target_local_date.isoformat()}")
    print(f"Status       : {result.status.value}")
    print(f"Revision     : {result.revision}")
    for status in PhaseStatus:
        names = [p.phase.value for p in result.phases if p.status is status]
        print(f"{status.value.title():<13}: {', '.join(names) if names else '-'}")
    print(f"Decision ID  : {result.decision_id or '-'}")
    print(f"Plan ID      : {result.training_plan_id or '-'}")
    print(f"Prescription : {result.prescription_id or '-'}")
    print(f"Briefing     : {'available' if result.morning_briefing_available else 'unavailable'}")
    codes = [warning.code for warning in result.warnings]
    if result.failure is not None and result.failure.code not in codes:
        codes.append(result.failure.code)
    print(f"Codes        : {', '.join(codes) if codes else '-'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Production Daily Runtime candidate")
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--health-db")
    parser.add_argument("--biomarkers-db")
    parser.add_argument("--decisions-db")
    parser.add_argument("--training-plan-db")
    parser.add_argument("--runtime-audit-db")
    parser.add_argument("--fit-source")
    args = parser.parse_args()
    return run_production_daily_runtime(
        target_date=args.date,
        health_db_path=args.health_db,
        biomarkers_db_path=args.biomarkers_db,
        decisions_db_path=args.decisions_db,
        training_plan_db_path=args.training_plan_db,
        runtime_audit_db_path=args.runtime_audit_db,
        fit_source_path=args.fit_source,
    )


if __name__ == "__main__":
    raise SystemExit(main())
