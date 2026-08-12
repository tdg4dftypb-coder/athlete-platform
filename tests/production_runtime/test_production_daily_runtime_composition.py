from datetime import date

import duckdb

from production_runtime.production_composition import create_production_daily_runtime


def options(tmp_path):
    fit = tmp_path / "fits"
    fit.mkdir()
    return dict(
        target_local_date=date(2026, 8, 11),
        health_db_path=tmp_path / "health.duckdb",
        biomarkers_db_path=tmp_path / "bio.duckdb",
        decisions_db_path=tmp_path / "decisions.duckdb",
        training_plan_db_path=tmp_path / "plan.duckdb",
        runtime_audit_db_path=tmp_path / "runtime.duckdb",
        activity_reconciliation_db_path=tmp_path / "reconciliation.duckdb",
        fit_source_path=fit,
    )


def test_owned_resources_close_on_success(tmp_path):
    paths = options(tmp_path)
    with create_production_daily_runtime(**paths):
        pass
    for name in ("health_db_path", "biomarkers_db_path", "decisions_db_path"):
        connection = duckdb.connect(str(paths[name]))
        connection.close()


def test_owned_resources_close_on_exceptional_exit(tmp_path):
    paths = options(tmp_path)
    try:
        with create_production_daily_runtime(**paths):
            raise RuntimeError("bounded test exit")
    except RuntimeError:
        pass
    connection = duckdb.connect(str(paths["decisions_db_path"]))
    connection.close()
