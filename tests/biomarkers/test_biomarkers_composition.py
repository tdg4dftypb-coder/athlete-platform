"""
Regression Test Suite for Biomarkers Composition Root and Context (Sprint 7C.3).
"""

import os
from pathlib import Path
import pytest

from biomarkers.composition import BiomarkersApplicationContext, build_repository_from_env
from biomarkers.persistence.duckdb_repository import DuckDBLaboratoryRepository
from biomarkers.repository import InMemoryLaboratoryRepository


def test_build_repository_from_env_with_db_path(tmp_path: Path) -> None:
    db_file = str(tmp_path / "custom_test.duckdb")

    # 1. Passing db_path explicitly selects DuckDBLaboratoryRepository
    repo = build_repository_from_env(db_path=db_file)
    assert isinstance(repo, DuckDBLaboratoryRepository)
    repo.close()

    # 2. Passing db_path to BiomarkersApplicationContext selects DuckDBLaboratoryRepository
    ctx = BiomarkersApplicationContext(db_path=db_file)
    assert isinstance(ctx.repository, DuckDBLaboratoryRepository)
    ctx.repository.close()


def test_build_repository_from_env_default_in_memory() -> None:
    # Without env vars or db_path, defaults to InMemoryLaboratoryRepository
    old_env = os.environ.pop("BIOMARKERS_REPOSITORY", None)
    try:
        repo = build_repository_from_env()
        assert isinstance(repo, InMemoryLaboratoryRepository)
    finally:
        if old_env is not None:
            os.environ["BIOMARKERS_REPOSITORY"] = old_env
