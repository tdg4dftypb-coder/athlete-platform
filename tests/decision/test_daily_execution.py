from datetime import date, datetime, timezone
import pytest
from zoneinfo import ZoneInfo

from decision.daily_execution import (
    DailyCoordinatorOutcome,
    DailyExecutionLedgerState,
    DailyExecutionRecord,
    calculate_local_run_date,
)


def test_calculate_local_run_date_timezone_boundary():
    # UTC date is 2026-08-07, but in Europe/Warsaw (+2h) it is 2026-08-08 01:30
    utc_dt = datetime(2026, 8, 7, 23, 30, 0, tzinfo=timezone.utc)
    local_d = calculate_local_run_date(utc_dt, "Europe/Warsaw")
    assert local_d == date(2026, 8, 8)

    # Naive datetime gets converted assuming UTC
    naive_dt = datetime(2026, 8, 7, 23, 30, 0)
    local_d_naive = calculate_local_run_date(naive_dt, "Europe/Warsaw")
    assert local_d_naive == date(2026, 8, 8)


def test_daily_execution_record_immutability():
    dt = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    rec = DailyExecutionRecord(
        run_date=date(2026, 8, 7),
        status=DailyExecutionLedgerState.RUNNING,
        decision_id="decision-123",
        timezone_name="Europe/Warsaw",
        started_at=dt,
    )
    assert rec.run_date == date(2026, 8, 7)
    assert rec.status == DailyExecutionLedgerState.RUNNING
    assert rec.completed_at is None

    with pytest.raises(AttributeError):
        rec.status = DailyExecutionLedgerState.COMPLETED  # Frozen dataclass
