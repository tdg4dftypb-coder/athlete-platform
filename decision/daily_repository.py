"""Daily Execution Repository protocol and exceptions."""
from datetime import date, datetime
from typing import Optional, Protocol, runtime_checkable

from decision.daily_execution import DailyExecutionRecord, DailyExecutionLedgerState


class DailyExecutionRepositoryError(Exception):
    """Base exception for Daily Execution Repository infrastructure failures."""


class DailyExecutionConflictError(DailyExecutionRepositoryError):
    """Raised when an atomic reservation conflict occurs."""


@runtime_checkable
class DailyExecutionRepository(Protocol):
    """Repository protocol boundary for persisting and managing daily execution records."""

    def reserve(self, record: DailyExecutionRecord) -> None:
        """Atomically reserves a run_date in RUNNING state. Raises DailyExecutionConflictError if already present."""
        ...

    def get_by_run_date(self, run_date: date) -> Optional[DailyExecutionRecord]:
        """Retrieves a DailyExecutionRecord by its local calendar date."""
        ...

    def mark_completed(
        self,
        run_date: date,
        decision_id: str,
        expected_attempt_count: int,
        completed_at: datetime,
    ) -> DailyExecutionRecord:
        """Updates a daily execution record status to COMPLETED if attempt match."""
        ...

    def mark_failed(
        self,
        run_date: date,
        decision_id: str,
        expected_attempt_count: int,
        error_message: str,
        completed_at: datetime,
    ) -> DailyExecutionRecord:
        """Updates a daily execution record status to FAILED if attempt match."""
        ...

    def takeover_retry(
        self,
        run_date: date,
        decision_id: str,
        expected_attempt_count: int,
        expected_status: DailyExecutionLedgerState,
        new_started_at: datetime,
        new_lease_expires_at: datetime,
    ) -> DailyExecutionRecord:
        """Takes over an expired RUNNING or FAILED execution attempt, incrementing attempt_count and updating lease."""
        ...
