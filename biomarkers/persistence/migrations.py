"""
DuckDB Idempotent Schema Migrations for Biomarkers Domain.
"""

from datetime import datetime, timezone
import duckdb

from biomarkers.persistence.schema import (
    CREATE_LABORATORY_IMPORT_RUNS_TABLE,
    CREATE_LABORATORY_OBSERVATIONS_TABLE,
    CREATE_LABORATORY_REPORTS_TABLE,
    CREATE_LABORATORY_TOMBSTONES_TABLE,
    CREATE_SCHEMA_VERSION_TABLE,
)

SCHEMA_VERSION = 1


def run_migrations(conn: duckdb.DuckDBPyConnection) -> int:
    """
    Executes idempotent migrations on DuckDB connection inside a single transaction.
    Returns current schema_version.
    """
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(CREATE_SCHEMA_VERSION_TABLE)

        # Check current version
        res = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current_version = res[0] if res and res[0] is not None else 0

        if current_version < 1:
            conn.execute(CREATE_LABORATORY_REPORTS_TABLE)
            conn.execute(CREATE_LABORATORY_IMPORT_RUNS_TABLE)
            conn.execute(CREATE_LABORATORY_OBSERVATIONS_TABLE)
            conn.execute(CREATE_LABORATORY_TOMBSTONES_TABLE)

            now_utc = datetime.now(timezone.utc)
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                [1, now_utc],
            )
            current_version = 1

        conn.execute("COMMIT")
        return current_version
    except Exception:
        conn.execute("ROLLBACK")
        raise
