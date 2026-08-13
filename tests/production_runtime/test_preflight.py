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
        "activity_reconciliation_db_path": tmp_path / "reconciliation.duckdb",
        "plan_adaptation_db_path": tmp_path / "adaptation.duckdb",
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
        connection.execute("INSERT INTO training_plans VALUES ('plan-1', ?, ?)", [TARGET, date(2026, 8, 18)])
    connection.close()
    return paths


def test_read_only_preflight_success_without_creating_runtime_database(tmp_path):
    paths = fixture_paths(tmp_path)
    checks = run_preflight_checks(TARGET, **paths)
    assert all(check.passed for check in checks), checks
    assert not paths["runtime_audit_db_path"].exists()
    assert not paths["activity_reconciliation_db_path"].exists()
    assert not paths["plan_adaptation_db_path"].exists()
    continuity=next(x for x in checks if x.name=="continuation_specification")
    assert continuity.passed and "future_readiness_warning" in continuity.detail


def test_preflight_reports_missing_plan(tmp_path):
    checks = run_preflight_checks(TARGET, **fixture_paths(tmp_path, seed_plan=False))
    plan = next(check for check in checks if check.name == "applicable_training_plan")
    assert not plan.passed


def test_preflight_reports_required_continuation_specification_unavailable_read_only(tmp_path):
    paths=fixture_paths(tmp_path)
    connection=duckdb.connect(str(paths["training_plan_db_path"]));connection.execute(
        "UPDATE training_plans SET end_date=?",[TARGET]);connection.close()
    check=next(x for x in run_preflight_checks(TARGET,**paths) if x.name=="continuation_specification")
    assert not check.passed and "extension_required=yes" in check.detail


def test_preflight_plan_resolution_includes_extended_revisions(tmp_path):
    from tests.training_plan.test_horizon_continuity import source,spec
    from training_plan.continuity import TrainingPlanHorizonExtensionService
    from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
    from datetime import datetime,timezone
    paths=fixture_paths(tmp_path,seed_plan=False);path=paths["training_plan_db_path"]
    connection=duckdb.connect(str(path));connection.execute("DROP TABLE training_plans");connection.close()
    repo=DuckDbTrainingPlanRepository(path);base=source();repo.save(base)
    extended=TrainingPlanHorizonExtensionService().extend(base,spec(),date(2026,9,9),generated_at=datetime(2026,9,2,tzinfo=timezone.utc)).plan
    repo.append_revision(base.version,extended)
    checks=run_preflight_checks(date(2026,9,20),**paths)
    assert next(x for x in checks if x.name=="applicable_training_plan").passed


def test_preflight_reports_configured_target_horizon_calculation(tmp_path):
    from tests.training_plan.test_horizon_continuity import source,spec
    from training_plan.persistence.duckdb_repository import DuckDbTrainingPlanRepository
    paths=fixture_paths(tmp_path,seed_plan=False);path=paths["training_plan_db_path"]
    connection=duckdb.connect(str(path));connection.execute("DROP TABLE training_plans");connection.close()
    repo=DuckDbTrainingPlanRepository(path);repo.save(source());repo.save_continuation_specification(spec())
    check=next(x for x in run_preflight_checks(date(2026,8,14),**paths) if x.name=="continuation_specification")
    assert check.passed and "target_date=2026-09-11" in check.detail
    assert "remaining_buffer_days=23" in check.detail and "extension_required=yes" in check.detail


def test_preflight_reports_missing_database_and_source(tmp_path):
    paths = fixture_paths(tmp_path)
    paths["health_db_path"].unlink()
    paths["fit_source_path"].rmdir()
    checks = run_preflight_checks(TARGET, **paths)
    assert not next(check for check in checks if check.name == "health_db").passed
    assert not next(check for check in checks if check.name == "fit_source").passed
