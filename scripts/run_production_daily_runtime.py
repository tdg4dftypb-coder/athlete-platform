"""Production-candidate CLI for the authoritative daily runtime coordinator."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from production_runtime.clock import SystemUtcRuntimeClock, target_local_date_at
from production_runtime.models import PhaseStatus, RuntimeStatus
from production_runtime.diagnostics import RuntimeResumability
from production_runtime.persistence import get_default_runtime_audit_db_path


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
    operation: str = "new",
    resume_runtime_id: str | None = None,
    status_reader=None,
) -> int:
    runtime_clock = clock or SystemUtcRuntimeClock()
    resolved_date = target_date or target_local_date_at(runtime_clock.now_utc())
    try:
        container = None
        if operation == "scheduled":
            snapshot = _scheduled_snapshot(
                resolved_date, runtime_audit_db_path, status_reader
            )
            if snapshot is not None:
                if snapshot.status is RuntimeStatus.COMPLETED:
                    _print_scheduled_noop(snapshot)
                    return 0
                if (
                    snapshot.status is RuntimeStatus.RUNNING
                    and snapshot.resumability is RuntimeResumability.RESUME_SAME_ATTEMPT
                ):
                    resume_runtime_id = snapshot.runtime_id
                else:
                    print(
                        "Production Daily Runtime requires operator action: "
                        f"status={snapshot.status.value} resume={snapshot.resumability.value}",
                        file=sys.stderr,
                    )
                    return 1
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
                result = (
                    container.runtime.resume_attempt(resume_runtime_id)
                    if resume_runtime_id else container.runtime.run_new_attempt(resolved_date)
                )
        else:
            result = (
                coordinator.resume_attempt(resume_runtime_id)
                if resume_runtime_id else coordinator.run_new_attempt(resolved_date)
            )
        _print_result(result)
        return 0 if result.status is RuntimeStatus.COMPLETED else 1
    except Exception as error:
        print(f"Production Daily Runtime Error: {type(error).__name__}", file=sys.stderr)
        return 1


def _scheduled_snapshot(target_date, runtime_audit_db_path, reader):
    if reader is not None:
        return reader.get_latest_for_date(target_date)
    path = get_default_runtime_audit_db_path(runtime_audit_db_path)
    if not path.is_file():
        return None
    from production_runtime.diagnostics_composition import create_runtime_operational_status_reader
    return create_runtime_operational_status_reader(path).get_latest_for_date(target_date)


def _print_scheduled_noop(snapshot) -> None:
    print("Production Daily Runtime Scheduler")
    print(f"Target date  : {snapshot.target_local_date.isoformat()}")
    print(f"Runtime ID   : {snapshot.runtime_id}")
    print(f"Status       : {snapshot.status.value}")
    print(f"Revision     : {snapshot.revision}")
    print("Action       : no-op (already completed)")


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--scheduled", action="store_true")
    mode.add_argument("--resume", metavar="RUNTIME_ID")
    mode.add_argument("--new-attempt", action="store_true")
    args = parser.parse_args()
    return run_production_daily_runtime(
        target_date=args.date,
        health_db_path=args.health_db,
        biomarkers_db_path=args.biomarkers_db,
        decisions_db_path=args.decisions_db,
        training_plan_db_path=args.training_plan_db,
        runtime_audit_db_path=args.runtime_audit_db,
        fit_source_path=args.fit_source,
        operation="scheduled" if args.scheduled else "new",
        resume_runtime_id=args.resume,
    )


if __name__ == "__main__":
    raise SystemExit(main())
