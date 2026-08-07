"""Daily Execution models, statuses, and timezone-aware date calculations."""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo


class DailyExecutionLedgerState(str, Enum):
    """Persisted state of a daily execution attempt in the ledger database."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DailyCoordinatorOutcome(str, Enum):
    """Public outcome returned by DailyDecisionRuntimeCoordinator."""
    EXECUTED = "executed"
    SKIPPED_ALREADY_COMPLETED = "skipped_already_completed"
    SKIPPED_IN_PROGRESS = "skipped_in_progress"
    RECOVERED_COMPLETED = "recovered_completed"
    FAILED = "failed"


@dataclass(frozen=True)
class DailyExecutionRecord:
    """Immutable domain representation of a daily decision execution attempt."""
    run_date: date
    status: DailyExecutionLedgerState
    decision_id: str
    timezone_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    lease_expires_at: Optional[datetime] = None
    attempt_count: int = 1
    error_message: Optional[str] = None


def calculate_local_run_date(now_dt: datetime, tz_name: str = "Europe/Warsaw") -> date:
    """Computes the athlete's local calendar date given a datetime and timezone string."""
    if not isinstance(now_dt, datetime):
        raise TypeError("now_dt must be a datetime instance")

    # Ensure datetime is timezone-aware
    if now_dt.tzinfo is None:
        aware_dt = now_dt.replace(tzinfo=timezone.utc)
    else:
        aware_dt = now_dt

    local_dt = aware_dt.astimezone(ZoneInfo(tz_name))
    return local_dt.date()
