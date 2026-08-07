import os
import pytest

from decision.persistence.paths import get_default_decisions_db_path, PROJECT_ROOT


def test_get_default_decisions_db_path_cwd_independence(tmp_path, monkeypatch):
    # Change current working directory to a temporary path
    monkeypatch.chdir(tmp_path)

    default_path = get_default_decisions_db_path()

    # Must resolve relative to PROJECT_ROOT, NOT current working directory
    expected = PROJECT_ROOT / "data" / "database" / "decisions.duckdb"
    assert default_path == expected
    assert not (tmp_path / "data" / "database" / "decisions.duckdb").exists()


def test_get_default_decisions_db_path_with_relative_override():
    rel_override = "custom/db/path.duckdb"
    resolved = get_default_decisions_db_path(rel_override)
    assert resolved == PROJECT_ROOT / "custom" / "db" / "path.duckdb"


def test_get_default_decisions_db_path_with_absolute_override(tmp_path):
    abs_override = tmp_path / "abs_decisions.duckdb"
    resolved = get_default_decisions_db_path(abs_override)
    assert resolved == abs_override
