"""Minimal production composition for runtime audit persistence only."""
from pathlib import Path
from typing import Union

from production_runtime.persistence import (
    DuckDbRuntimeAuditRepository,
    get_default_runtime_audit_db_path,
)


def create_runtime_audit_repository(
    db_path: Union[str, Path, None] = None,
) -> DuckDbRuntimeAuditRepository:
    return DuckDbRuntimeAuditRepository(get_default_runtime_audit_db_path(db_path))
