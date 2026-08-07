import os
from pathlib import Path
import pytest

from decision.persistence.paths import PROJECT_ROOT, get_default_decisions_db_path


def test_project_root_points_to_workspace_root():
    assert PROJECT_ROOT.name == "athlete-platform"
    assert (PROJECT_ROOT / "decision").is_dir()
    assert (PROJECT_ROOT / "morning_briefing").is_dir()


def test_default_decisions_db_path_without_override():
    res = get_default_decisions_db_path()
    assert res == PROJECT_ROOT / "data" / "database" / "decisions.duckdb"
    assert "decision/data" not in str(res).replace("\\", "/")


def test_explicit_relative_override_relative_to_repo_root():
    res = get_default_decisions_db_path("custom/my_decisions.duckdb")
    assert res == PROJECT_ROOT / "custom" / "my_decisions.duckdb"
    assert "decision/custom" not in str(res).replace("\\", "/")


def test_explicit_absolute_override_preserved():
    abs_path = Path("/tmp/absolute_decisions.duckdb")
    res = get_default_decisions_db_path(abs_path)
    assert res == abs_path


def test_env_relative_override_relative_to_repo_root(monkeypatch):
    monkeypatch.setenv("DECISIONS_DB_PATH", "env_dir/env_decisions.duckdb")
    res = get_default_decisions_db_path()
    assert res == PROJECT_ROOT / "env_dir" / "env_decisions.duckdb"


def test_env_absolute_override_preserved(monkeypatch):
    monkeypatch.setenv("DECISIONS_DB_PATH", "/tmp/env_abs_decisions.duckdb")
    res = get_default_decisions_db_path()
    assert res == Path("/tmp/env_abs_decisions.duckdb")


def test_path_resolution_independent_of_cwd(monkeypatch, tmp_path):
    # Change working directory to a temporary directory
    monkeypatch.chdir(tmp_path)
    res_default = get_default_decisions_db_path()
    res_relative = get_default_decisions_db_path("rel/test.duckdb")

    assert res_default == PROJECT_ROOT / "data" / "database" / "decisions.duckdb"
    assert res_relative == PROJECT_ROOT / "rel" / "test.duckdb"
    assert str(tmp_path) not in str(res_default)
