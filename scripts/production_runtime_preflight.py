"""Read-only Gate B preflight CLI."""
import argparse
from datetime import date

from production_runtime.clock import SystemUtcRuntimeClock, target_local_date_at
from production_runtime.preflight import run_preflight_checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ProductionDailyRuntime cutover preflight")
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--health-db")
    parser.add_argument("--biomarkers-db")
    parser.add_argument("--decisions-db")
    parser.add_argument("--training-plan-db")
    parser.add_argument("--runtime-audit-db")
    parser.add_argument("--activity-reconciliation-db")
    parser.add_argument("--fit-source")
    args = parser.parse_args()
    target = args.date or target_local_date_at(SystemUtcRuntimeClock().now_utc())
    checks = run_preflight_checks(
        target, health_db_path=args.health_db, biomarkers_db_path=args.biomarkers_db,
        decisions_db_path=args.decisions_db, training_plan_db_path=args.training_plan_db,
        runtime_audit_db_path=args.runtime_audit_db, fit_source_path=args.fit_source,
        activity_reconciliation_db_path=args.activity_reconciliation_db,
    )
    print(f"Production Runtime Preflight — {target.isoformat()}")
    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL':<4} {check.name}: {check.detail}")
    return 0 if all(check.passed for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
