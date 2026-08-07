from datetime import date, datetime, timezone
import duckdb
import pytest

from decision.daily_execution import DailyExecutionLedgerState, DailyExecutionRecord
from decision.daily_repository import DailyExecutionConflictError
from decision.persistence import DuckDbDailyExecutionRepository


@pytest.fixture
def in_memory_daily_repo():
    conn = duckdb.connect(":memory:")
    return DuckDbDailyExecutionRepository(conn=conn)


def test_duckdb_daily_repo_reserve_and_get(in_memory_daily_repo):
    t_start = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    t_lease = datetime(2026, 8, 7, 10, 15, 0, tzinfo=timezone.utc)
    d = date(2026, 8, 7)

    rec = DailyExecutionRecord(
        run_date=d,
        status=DailyExecutionLedgerState.RUNNING,
        decision_id="decision-res-01",
        timezone_name="Europe/Warsaw",
        started_at=t_start,
        lease_expires_at=t_lease,
    )

    in_memory_daily_repo.reserve(rec)

    fetched = in_memory_daily_repo.get_by_run_date(d)
    assert fetched is not None
    assert fetched.run_date == d
    assert fetched.status == DailyExecutionLedgerState.RUNNING
    assert fetched.decision_id == "decision-res-01"
    assert fetched.timezone_name == "Europe/Warsaw"
    assert fetched.attempt_count == 1
    assert fetched.completed_at is None
    assert fetched.lease_expires_at == t_lease


def test_duckdb_daily_repo_reserve_conflict(in_memory_daily_repo):
    t_start = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    d = date(2026, 8, 7)
    rec1 = DailyExecutionRecord(
        run_date=d,
        status=DailyExecutionLedgerState.RUNNING,
        decision_id="decision-01",
        timezone_name="Europe/Warsaw",
        started_at=t_start,
    )
    rec2 = DailyExecutionRecord(
        run_date=d,
        status=DailyExecutionLedgerState.RUNNING,
        decision_id="decision-02",
        timezone_name="Europe/Warsaw",
        started_at=t_start,
    )

    in_memory_daily_repo.reserve(rec1)

    with pytest.raises(DailyExecutionConflictError):
        in_memory_daily_repo.reserve(rec2)


def test_duckdb_daily_repo_mark_completed_and_failed(in_memory_daily_repo):
    t_start = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    d = date(2026, 8, 7)
    rec = DailyExecutionRecord(
        run_date=d,
        status=DailyExecutionLedgerState.RUNNING,
        decision_id="decision-01",
        timezone_name="Europe/Warsaw",
        started_at=t_start,
    )

    in_memory_daily_repo.reserve(rec)

    t_comp = datetime(2026, 8, 7, 10, 5, 0, tzinfo=timezone.utc)
    updated = in_memory_daily_repo.mark_completed(d, "decision-01", t_comp)

    assert updated.status == DailyExecutionLedgerState.COMPLETED
    assert updated.completed_at == t_comp
    assert updated.lease_expires_at is None

    # Test mark failed on another date
    d2 = date(2026, 8, 8)
    rec2 = DailyExecutionRecord(
        run_date=d2,
        status=DailyExecutionLedgerState.RUNNING,
        decision_id="decision-02",
        timezone_name="Europe/Warsaw",
        started_at=t_start,
    )
    in_memory_daily_repo.reserve(rec2)

    failed = in_memory_daily_repo.mark_failed(d2, "ValueError: Timeout", t_comp)
    assert failed.status == DailyExecutionLedgerState.FAILED
    assert failed.error_message == "ValueError: Timeout"


def test_duckdb_daily_repo_takeover_retry(in_memory_daily_repo):
    t_start = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    d = date(2026, 8, 7)
    rec = DailyExecutionRecord(
        run_date=d,
        status=DailyExecutionLedgerState.FAILED,
        decision_id="decision-01",
        timezone_name="Europe/Warsaw",
        started_at=t_start,
    )
    in_memory_daily_repo.reserve(rec)

    t_retry_start = datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc)
    t_retry_lease = datetime(2026, 8, 7, 11, 15, 0, tzinfo=timezone.utc)

    taken_over = in_memory_daily_repo.takeover_retry(
        run_date=d,
        decision_id="decision-01",
        new_started_at=t_retry_start,
        new_lease_expires_at=t_retry_lease,
    )

    assert taken_over.status == DailyExecutionLedgerState.RUNNING
    assert taken_over.attempt_count == 2
    assert taken_over.started_at == t_retry_start
    assert taken_over.lease_expires_at == t_retry_lease
