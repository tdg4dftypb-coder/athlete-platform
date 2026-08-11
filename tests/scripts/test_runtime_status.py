from datetime import date, datetime, timedelta, timezone

from production_runtime import (
    RUNTIME_CONTRACT_VERSION,
    ProductionDailyRuntimeResult,
    RuntimeOperationalStatusReader,
    RuntimeStatus,
    logical_execution_key,
)
from production_runtime.persistence import DuckDbRuntimeAuditRepository
from scripts.runtime_status import run_runtime_status


TARGET = date(2026, 8, 11)
START = datetime(2026, 8, 11, 5, 0, tzinfo=timezone.utc)


class FixedClock:
    def now_utc(self):
        return START + timedelta(minutes=1)


def attempt(runtime_id="runtime-cli", started_at=START):
    return ProductionDailyRuntimeResult(
        runtime_id=runtime_id,
        logical_execution_key=logical_execution_key(TARGET),
        revision=1,
        contract_version=RUNTIME_CONTRACT_VERSION,
        target_local_date=TARGET,
        timezone_name="Europe/Warsaw",
        started_at_utc=started_at,
        completed_at_utc=None,
        status=RuntimeStatus.RUNNING,
    )


def setup_reader(tmp_path, *attempts):
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    for item in attempts:
        repo.append(item)
    return repo, RuntimeOperationalStatusReader(repo, FixedClock())


def test_cli_latest_output_is_compact_and_operator_friendly(tmp_path, capsys) -> None:
    _, reader = setup_reader(tmp_path, attempt())
    assert run_runtime_status([], reader=reader) == 0
    output = capsys.readouterr().out
    assert "Production Runtime Status" in output
    assert "Runtime     : runtime-cli" in output
    assert "Revision    : 1" in output
    assert "Status      : RUNNING" in output
    assert "Resume      : RESUME_SAME_ATTEMPT" in output
    assert "ingestion" in output
    assert "NOT RUN" in output


def test_cli_explicit_date_and_all_attempts(tmp_path, capsys) -> None:
    _, reader = setup_reader(
        tmp_path,
        attempt("runtime-a", START),
        attempt("runtime-b", START + timedelta(seconds=1)),
    )
    assert run_runtime_status(["--date", TARGET.isoformat()], reader=reader) == 0
    latest_output = capsys.readouterr().out
    assert "runtime-b" in latest_output
    assert "runtime-a" not in latest_output
    assert run_runtime_status(
        ["--date", TARGET.isoformat(), "--all-attempts"], reader=reader
    ) == 0
    all_output = capsys.readouterr().out
    assert "runtime-a" in all_output
    assert "runtime-b" in all_output


def test_cli_explicit_runtime_id(tmp_path, capsys) -> None:
    _, reader = setup_reader(tmp_path, attempt("runtime-exact"))
    assert run_runtime_status(["--runtime-id", "runtime-exact"], reader=reader) == 0
    assert "Runtime     : runtime-exact" in capsys.readouterr().out


def test_cli_no_data_is_distinct_from_unavailable(tmp_path, capsys) -> None:
    _, reader = setup_reader(tmp_path)
    assert run_runtime_status([], reader=reader) == 0
    assert "Health      : NO_DATA" in capsys.readouterr().out
    missing = tmp_path / "missing.duckdb"
    assert run_runtime_status(["--runtime-audit-db", str(missing)]) == 2
    captured = capsys.readouterr()
    assert "Runtime audit unavailable" in captured.err
    assert not missing.exists()


def test_cli_does_not_add_audit_revisions(tmp_path, capsys) -> None:
    repo, reader = setup_reader(tmp_path, attempt())
    before = repo.get_by_runtime_id("runtime-cli")
    assert run_runtime_status([], reader=reader) == 0
    capsys.readouterr()
    after = repo.get_by_runtime_id("runtime-cli")
    assert after == before
    assert after.revision == 1


def test_cli_real_composition_is_read_only(tmp_path, capsys) -> None:
    db_path = tmp_path / "audit.duckdb"
    repo = DuckDbRuntimeAuditRepository(db_path)
    repo.append(attempt())
    assert run_runtime_status(["--runtime-audit-db", str(db_path)]) == 0
    assert "runtime-cli" in capsys.readouterr().out
    connection = __import__("duckdb").connect(str(db_path))
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM production_runtime_audit_revisions"
        ).fetchone()[0] == 1
    finally:
        connection.close()
