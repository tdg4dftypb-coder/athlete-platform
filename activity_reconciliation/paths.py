"""Canonical persistence path for activity reconciliation results."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Union


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_default_activity_reconciliation_db_path(
    override_path: Union[str, Path, None] = None,
) -> Path:
    raw_path = (
        override_path
        if override_path is not None
        else os.environ.get("ACTIVITY_RECONCILIATION_DB_PATH")
    )
    if raw_path is None:
        return PROJECT_ROOT / "data" / "database" / "activity_reconciliation.duckdb"
    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path
