"""Canonical path resolution without opening or creating a database."""
from pathlib import Path
from typing import Union

from production_runtime.paths import get_default_health_db_path


def get_default_context_memory_db_path(
    override_path: Union[str, Path, None] = None,
) -> Path:
    """Context Memory shares the canonical Health DB, using separate tables."""
    return get_default_health_db_path(override_path)
