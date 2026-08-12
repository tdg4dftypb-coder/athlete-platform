"""Read-only Gate B preflight checks for ProductionDailyRuntime cutover."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import os

import duckdb

from production_runtime.persistence import get_default_runtime_audit_db_path
from production_runtime.diagnostics_composition import create_runtime_operational_status_reader
from production_runtime.paths import PROJECT_ROOT, get_default_fit_activity_source_path, get_default_health_db_path
from decision.persistence.paths import get_default_decisions_db_path
from training_plan.persistence.paths import get_default_training_plan_db_path
from activity_reconciliation.paths import get_default_activity_reconciliation_db_path


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    passed: bool
    detail: str


def run_preflight_checks(
    target_date: date,
    *,
    health_db_path=None,
    biomarkers_db_path=None,
    decisions_db_path=None,
    training_plan_db_path=None,
    runtime_audit_db_path=None,
    activity_reconciliation_db_path=None,
    fit_source_path=None,
    python_path=None,
    working_directory=None,
) -> tuple[PreflightCheck, ...]:
    health = get_default_health_db_path(health_db_path)
    biomarkers = _anchored(biomarkers_db_path, "data/database/biomarkers.duckdb")
    decisions = get_default_decisions_db_path(decisions_db_path)
    plans = get_default_training_plan_db_path(training_plan_db_path)
    runtime = get_default_runtime_audit_db_path(runtime_audit_db_path)
    reconciliation = get_default_activity_reconciliation_db_path(
        activity_reconciliation_db_path
    )
    source = get_default_fit_activity_source_path(fit_source_path)
    python = Path(python_path) if python_path else PROJECT_ROOT / ".venv/bin/python"
    working = Path(working_directory) if working_directory else PROJECT_ROOT
    checks = [
        PreflightCheck("working_directory", working.is_dir(), str(working)),
        PreflightCheck("python", python.is_file() and os.access(python, os.X_OK), str(python)),
        PreflightCheck("command", (PROJECT_ROOT / "scripts/run_production_daily_runtime.py").is_file(), "scripts.run_production_daily_runtime --scheduled"),
        PreflightCheck("fit_source", source.is_dir(), str(source)),
    ]
    for name, path in (("health_db", health), ("biomarkers_db", biomarkers), ("decisions_db", decisions), ("training_plan_db", plans)):
        checks.append(_readable_database(name, path))
    checks.append(_plan_check(plans, target_date))
    checks.append(_existing_or_creatable_database(
        "activity_reconciliation_db", reconciliation
    ))
    if runtime.is_file():
        checks.append(_readable_database("runtime_audit_db", runtime))
        try:
            snapshot = create_runtime_operational_status_reader(runtime).get_latest_for_date(target_date)
            detail = "no attempt" if snapshot is None else (
                f"{snapshot.status.value}/{snapshot.resumability.value} runtime={snapshot.runtime_id}"
            )
            checks.append(PreflightCheck("runtime_state", True, detail))
        except Exception as error:
            checks.append(PreflightCheck("runtime_state", False, f"unreadable: {type(error).__name__}"))
    else:
        parent = runtime.parent
        checks.append(PreflightCheck("runtime_audit_db", parent.is_dir() and os.access(parent, os.W_OK), f"new file under {parent}"))
        checks.append(PreflightCheck("runtime_state", True, "no audit database; scheduled policy will start new"))
    return tuple(checks)


def _anchored(value, default):
    path = Path(value) if value is not None else PROJECT_ROOT / default
    return path if path.is_absolute() else PROJECT_ROOT / path


def _readable_database(name, path):
    if not path.is_file():
        return PreflightCheck(name, False, f"missing: {path}")
    try:
        connection = duckdb.connect(str(path), read_only=True)
        connection.execute("SELECT 1").fetchone()
        connection.close()
        return PreflightCheck(name, True, str(path))
    except Exception as error:
        return PreflightCheck(name, False, f"unreadable: {type(error).__name__}")


def _existing_or_creatable_database(name, path):
    if path.is_file():
        return _readable_database(name, path)
    parent = path.parent
    return PreflightCheck(
        name,
        parent.is_dir() and os.access(parent, os.W_OK),
        f"new file under {parent}",
    )


def _plan_check(path, target_date):
    if not path.is_file():
        return PreflightCheck("applicable_training_plan", False, "training plan database missing")
    try:
        connection = duckdb.connect(str(path), read_only=True)
        row = connection.execute(
            "SELECT plan_id FROM training_plans WHERE start_date <= ? AND end_date >= ? LIMIT 1",
            [target_date, target_date],
        ).fetchone()
        connection.close()
        return PreflightCheck(
            "applicable_training_plan", row is not None,
            row[0] if row else f"none for {target_date.isoformat()}",
        )
    except Exception as error:
        return PreflightCheck("applicable_training_plan", False, f"unreadable: {type(error).__name__}")
