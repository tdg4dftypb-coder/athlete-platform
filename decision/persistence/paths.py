import os
from pathlib import Path
from typing import Union

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_default_decisions_db_path(override_path: Union[str, Path, None] = None) -> Path:
    """Resolves the default decisions DuckDB database path relative to project root."""
    if override_path is not None:
        p = Path(override_path)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p

    env_path = os.environ.get("DECISIONS_DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p

    return PROJECT_ROOT / "data" / "database" / "decisions.duckdb"
