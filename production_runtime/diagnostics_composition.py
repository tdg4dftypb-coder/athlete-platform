"""Read-only composition for runtime operational diagnostics."""
from datetime import timedelta
from pathlib import Path
from typing import Union

from production_runtime.clock import RuntimeClock
from production_runtime.diagnostics import RuntimeOperationalStatusReader
from production_runtime.persistence import (
    DuckDbRuntimeAuditRepository,
    get_default_runtime_audit_db_path,
)


def create_runtime_operational_status_reader(
    runtime_audit_db_path: Union[str, Path, None] = None,
    *,
    clock: RuntimeClock | None = None,
    stale_after: timedelta = RuntimeOperationalStatusReader.DEFAULT_STALE_AFTER,
) -> RuntimeOperationalStatusReader:
    repository = DuckDbRuntimeAuditRepository(
        get_default_runtime_audit_db_path(runtime_audit_db_path),
        read_only=True,
    )
    return RuntimeOperationalStatusReader(repository, clock, stale_after)
