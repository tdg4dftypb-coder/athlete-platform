"""Tests for scripts/run_daily_decision_runtime.py CLI runner."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest

from decision.daily_execution import (
    DailyCoordinatorOutcome,
    DailyExecutionLedgerState,
    DailyExecutionRecord,
)
from decision.daily_coordinator import CoordinatorExecutionResult
from scripts.run_daily_decision_runtime import run_daily_decision_runtime


def test_cli_executed_returns_zero_exit_code(capsys):
    rec = DailyExecutionRecord(
        run_date=date(2026, 8, 7),
        status=DailyExecutionLedgerState.COMPLETED,
        decision_id="dec-cli-001",
        timezone_name="Europe/Warsaw",
        started_at=datetime.now(timezone.utc),
        attempt_count=1,
    )
    mock_coord = MagicMock()
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.EXECUTED,
        run_date_str="2026-08-07",
        decision_id="dec-cli-001",
        record=rec,
    )

    exit_code = run_daily_decision_runtime(coordinator=mock_coord)

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Daily Decision Runtime" in captured
    assert "Run date    : 2026-08-07" in captured
    assert "Outcome     : executed" in captured
    assert "Decision ID : dec-cli-001" in captured
    assert "Attempt     : 1" in captured


def test_cli_skipped_already_completed_returns_zero_exit_code(capsys):
    mock_coord = MagicMock()
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.SKIPPED_ALREADY_COMPLETED,
        run_date_str="2026-08-07",
        decision_id="dec-cli-001",
    )

    exit_code = run_daily_decision_runtime(coordinator=mock_coord)

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Outcome     : skipped_already_completed" in captured
    assert "Decision ID : dec-cli-001" in captured


def test_cli_skipped_in_progress_returns_zero_exit_code(capsys):
    mock_coord = MagicMock()
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.SKIPPED_IN_PROGRESS,
        run_date_str="2026-08-07",
        decision_id="dec-cli-002",
    )

    exit_code = run_daily_decision_runtime(coordinator=mock_coord)

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Outcome     : skipped_in_progress" in captured


def test_cli_recovered_completed_returns_zero_exit_code(capsys):
    mock_coord = MagicMock()
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.RECOVERED_COMPLETED,
        run_date_str="2026-08-07",
        decision_id="dec-cli-003",
    )

    exit_code = run_daily_decision_runtime(coordinator=mock_coord)

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Outcome     : recovered_completed" in captured


def test_cli_failed_returns_non_zero_exit_code(capsys):
    rec = DailyExecutionRecord(
        run_date=date(2026, 8, 7),
        status=DailyExecutionLedgerState.FAILED,
        decision_id="dec-cli-failed",
        timezone_name="Europe/Warsaw",
        started_at=datetime.now(timezone.utc),
        attempt_count=1,
        error_message="RuntimeError: Database lock failure",
    )
    mock_coord = MagicMock()
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.FAILED,
        run_date_str="2026-08-07",
        decision_id="dec-cli-failed",
        record=rec,
    )

    exit_code = run_daily_decision_runtime(coordinator=mock_coord)

    assert exit_code == 1
    captured = capsys.readouterr().out
    assert "Outcome     : failed" in captured
    assert "Error       : RuntimeError: Database lock failure" in captured


def test_cli_same_day_execution_idempotency(tmp_path):
    h_db = tmp_path / "health.duckdb"
    b_db = tmp_path / "biomarkers.duckdb"
    d_db = tmp_path / "decisions.duckdb"

    # First run on local day
    exit1 = run_daily_decision_runtime(
        health_db_path=h_db,
        biomarkers_db_path=b_db,
        decisions_db_path=d_db,
    )
    assert exit1 == 0

    # Second run on same local day
    exit2 = run_daily_decision_runtime(
        health_db_path=h_db,
        biomarkers_db_path=b_db,
        decisions_db_path=d_db,
    )
    assert exit2 == 0


def test_cli_failed_retry_across_invocations():
    """Verifies failed attempt 1 can be retried by subsequent CLI invocation."""
    mock_coord = MagicMock()

    # First invocation fails
    rec_failed = DailyExecutionRecord(
        run_date=date(2026, 8, 7),
        status=DailyExecutionLedgerState.FAILED,
        decision_id="dec-retry-01",
        timezone_name="Europe/Warsaw",
        started_at=datetime.now(timezone.utc),
        attempt_count=1,
        error_message="RuntimeError: Temporary network issue",
    )
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.FAILED,
        run_date_str="2026-08-07",
        decision_id="dec-retry-01",
        record=rec_failed,
    )
    exit1 = run_daily_decision_runtime(coordinator=mock_coord)
    assert exit1 == 1

    # Second invocation succeeds (takeover_retry)
    rec_success = DailyExecutionRecord(
        run_date=date(2026, 8, 7),
        status=DailyExecutionLedgerState.COMPLETED,
        decision_id="dec-retry-01",
        timezone_name="Europe/Warsaw",
        started_at=datetime.now(timezone.utc),
        attempt_count=2,
    )
    mock_coord.run_daily_if_needed.return_value = CoordinatorExecutionResult(
        outcome=DailyCoordinatorOutcome.EXECUTED,
        run_date_str="2026-08-07",
        decision_id="dec-retry-01",
        record=rec_success,
    )
    exit2 = run_daily_decision_runtime(coordinator=mock_coord)
    assert exit2 == 0
