from datetime import date
import sys

import duckdb

from production_runtime.preflight import run_preflight_checks


TARGET = date(2026, 8, 11)


def fixture_paths(tmp_path, *, seed_plan=True):
    paths = {
        "health_db_path": tmp_path / "health.duckdb",
        "biomarkers_db_path": tmp_path / "biomarkers.duckdb",
        "decisions_db_path": tmp_path / "decisions.duckdb",
        "training_plan_db_path": tmp_path / "training_plan.duckdb",
        "runtime_audit_db_path": tmp_path / "runtime.duckdb",
        "fit_source_path": tmp_path / "fits",
        "python_path": sys.executable,
        "working_directory": tmp_path,
    }
    paths["fit_source_path"].mkdir()
    for name in ("health_db_path", "biomarkers_db_path", "decisions_db_path"):
        connection = duckdb.connect(str(paths[name]))
        connection.close()
    connection = duckdb.connect(str(paths["training_plan_db_path"]))
    connection.execute("CREATE TABLE training_plans(plan_id VARCHAR, start_date DATE, end_date DATE)")
    if seed_plan:
        connection.execute("INSERT INTO training_plans VALUES ('plan-1', ?, ?)", [TARGET, TARGET])
    connection.close()
    return paths


def test_read_only_preflight_success_without_creating_runtime_database(tmp_path):
    paths = fixture_paths(tmp_path)
    checks = run_preflight_checks(TARGET, **paths)
    assert all(check.passed for check in checks), checks
    assert not paths["runtime_audit_db_path"].exists()


def test_preflight_reports_missing_plan(tmp_path):
    checks = run_preflight_checks(TARGET, **fixture_paths(tmp_path, seed_plan=False))
    plan = next(check for check in checks if check.name == "applicable_training_plan")
    assert not plan.passed


def test_preflight_reports_missing_database_and_source(tmp_path):
    paths = fixture_paths(tmp_path)
    paths["health_db_path"].unlink()
    paths["fit_source_path"].rmdir()
    checks = run_preflight_checks(TARGET, **paths)
    assert not next(check for check in checks if check.name == "health_db").passed
    assert not next(check for check in checks if check.name == "fit_source").passed
