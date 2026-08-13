import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_default_plan_adaptation_db_path(override_path=None) -> Path:
    raw = override_path if override_path is not None else os.environ.get("PLAN_ADAPTATION_DB_PATH")
    if raw is None:
        return PROJECT_ROOT / "data" / "database" / "plan_adaptation.duckdb"
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path
