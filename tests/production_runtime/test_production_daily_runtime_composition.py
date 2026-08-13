from datetime import date
import os
import subprocess
import sys

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
        plan_adaptation_db_path=tmp_path / "adaptation.duckdb",
        fit_source_path=fit,
    )


def test_owned_resources_close_on_success(tmp_path):
    paths = options(tmp_path)
    with create_production_daily_runtime(**paths):
        assert not paths["plan_adaptation_db_path"].exists()
    assert not paths["plan_adaptation_db_path"].exists()
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


def test_import_path_resolution_and_composition_are_adaptation_db_side_effect_free(tmp_path):
    target = tmp_path / "canonical-like" / "plan_adaptation.duckdb"
    environment = dict(os.environ, PLAN_ADAPTATION_DB_PATH=str(target))
    subprocess.run(
        [sys.executable, "-c", (
            "import plan_adaptation; "
            "import production_runtime.production_composition; "
            "from plan_adaptation.paths import get_default_plan_adaptation_db_path; "
            "assert str(get_default_plan_adaptation_db_path())"
        )],
        cwd=os.getcwd(), env=environment, check=True,
    )
    assert not target.exists()
