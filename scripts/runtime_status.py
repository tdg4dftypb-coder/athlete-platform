"""Read-only CLI for Production Runtime operational audit diagnostics."""
import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

from production_runtime.diagnostics import (
    RuntimeOperationalHealth,
    RuntimeOperationalSnapshot,
    RuntimeOperationalStatusReader,
)
from production_runtime.diagnostics_composition import (
    create_runtime_operational_status_reader,
)
from production_runtime.repository import RuntimeAuditRepositoryError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect Production Runtime audit status without modifying it."
    )
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--date", type=date.fromisoformat, help="Target local date (YYYY-MM-DD)")
    selector.add_argument("--runtime-id", help="Exact runtime attempt ID")
    parser.add_argument(
        "--all-attempts",
        action="store_true",
        help="Show every attempt for --date instead of only the latest",
    )
    parser.add_argument("--runtime-audit-db", type=Path, help="Runtime audit DuckDB path")
    parser.add_argument(
        "--stale-after-minutes",
        type=int,
        default=30,
        help="RUNNING staleness threshold (default: 30)",
    )
    return parser


def run_runtime_status(
    argv: list[str] | None = None,
    *,
    reader: RuntimeOperationalStatusReader | None = None,
) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    if arguments.all_attempts and arguments.date is None:
        parser.error("--all-attempts requires --date")
    if arguments.stale_after_minutes <= 0:
        parser.error("--stale-after-minutes must be positive")

    try:
        status_reader = reader or create_runtime_operational_status_reader(
            arguments.runtime_audit_db,
            stale_after=timedelta(minutes=arguments.stale_after_minutes),
        )
        if arguments.runtime_id:
            snapshots = _one(status_reader.get_by_runtime_id(arguments.runtime_id))
        elif arguments.date and arguments.all_attempts:
            snapshots = status_reader.list_for_date(arguments.date)
        elif arguments.date:
            snapshots = _one(status_reader.get_latest_for_date(arguments.date))
        else:
            snapshots = _one(status_reader.get_latest())
    except RuntimeAuditRepositoryError as error:
        print(f"Runtime audit unavailable: {error}", file=sys.stderr)
        return 2

    if not snapshots:
        print("Production Runtime Status")
        print(f"Health      : {RuntimeOperationalHealth.NO_DATA.value.upper()}")
        print("Attempt     : none")
        return 0

    for index, snapshot in enumerate(snapshots):
        if index:
            print()
        _print_snapshot(snapshot)
    return 0


def _one(snapshot: RuntimeOperationalSnapshot | None) -> tuple[RuntimeOperationalSnapshot, ...]:
    return () if snapshot is None else (snapshot,)


def _print_snapshot(snapshot: RuntimeOperationalSnapshot) -> None:
    print("Production Runtime Status")
    print(f"Target date : {snapshot.target_local_date.isoformat()}")
    print(f"Runtime     : {snapshot.runtime_id}")
    print(f"Logical key : {snapshot.logical_execution_key}")
    print(f"Revision    : {snapshot.revision}")
    print(f"Status      : {snapshot.status.value.upper()}")
    print(f"Health      : {snapshot.health.value.upper()}")
    print(f"Resume      : {snapshot.resumability.value.upper()}")
    print(f"Stale       : {'yes' if snapshot.stale_running else 'no'}")
    print(f"Last progress: {snapshot.last_durable_progress_at_utc.isoformat()}")
    if snapshot.next_expected_phase is not None:
        print(f"Next phase  : {snapshot.next_expected_phase.value}")

    print("Phases")
    for phase in snapshot.phases:
        status = phase.status.value.upper() if phase.status is not None else "NOT RUN"
        suffix = ""
        if phase.present:
            suffix = f" changed={'yes' if phase.changed_state else 'no'}"
            if phase.item_count is not None:
                suffix += f" count={phase.item_count}"
            if phase.artifact_ids:
                suffix += f" artifacts={len(phase.artifact_ids)}"
        print(f"  {phase.phase.value:<34} {status}{suffix}")

    if snapshot.warnings:
        print("Warnings")
        for warning in snapshot.warnings:
            source = f" [{warning.source}]" if warning.source else ""
            detail = f": {warning.detail}" if warning.detail else ""
            print(f"  {warning.code}{source}{detail}")
    else:
        print("Warnings    : none")

    if snapshot.failure is None:
        print("Failure     : none")
    else:
        phase = f" phase={snapshot.failure.phase.value}" if snapshot.failure.phase else ""
        detail = f": {snapshot.failure.detail}" if snapshot.failure.detail else ""
        print(f"Failure     : {snapshot.failure.code}{phase}{detail}")

    counters = snapshot.counters
    print("Counters")
    print(f"  activities_discovered       : {_optional(counters.activities_discovered)}")
    print(f"  activity_facts_created      : {_optional(counters.activity_facts_created)}")
    print(f"  activities_already_present  : {_optional(counters.activities_already_present)}")
    print(f"  reconciliations_created     : {_optional(counters.reconciliations_created)}")

    if snapshot.source_watermarks:
        print("Watermarks")
        for watermark in snapshot.source_watermarks:
            print(f"  {watermark.source}/{watermark.kind}: {watermark.value}")
    else:
        print("Watermarks  : none")


def _optional(value: int | None) -> str:
    return "unknown" if value is None else str(value)


def main() -> int:
    return run_runtime_status()


if __name__ == "__main__":
    raise SystemExit(main())
