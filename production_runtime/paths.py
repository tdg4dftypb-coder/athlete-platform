"""Canonical production paths needed by the ingestion runtime slice."""
import os
from pathlib import Path
from typing import Union


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_default_health_db_path(
    override_path: Union[str, Path, None] = None,
) -> Path:
    raw_path = override_path if override_path is not None else os.environ.get("HEALTH_DB_PATH")
    if raw_path is None:
        return PROJECT_ROOT / "data" / "database" / "health.duckdb"
    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_default_fit_activity_source_path(
    override_path: Union[str, Path, None] = None,
) -> Path:
    raw_path = override_path if override_path is not None else os.environ.get("FIT_ACTIVITY_SOURCE_PATH")
    if raw_path is not None:
        path = Path(raw_path)
        return path if path.is_absolute() else PROJECT_ROOT / path
    return Path.home() / "Documents" / "Zwift" / "Activities"


def get_zwift_activity_source_path(
    override_path: Union[str, Path, None] = None,
) -> Path | None:
    """Resolve only the explicit Zwift provider folder; no core default."""
    raw_path = override_path if override_path is not None else os.environ.get("ZWIFT_ACTIVITY_SOURCE_PATH")
    if raw_path is None:
        return None
    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path
