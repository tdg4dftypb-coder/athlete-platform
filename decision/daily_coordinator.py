"""Application-level coordinator for crash-safe, idempotent Automated Daily Decision Runtime."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Union
import uuid

from decision.daily_execution import (
    DailyCoordinatorOutcome,
    DailyExecutionLedgerState,
    DailyExecutionRecord,
    calculate_local_run_date,
)
from decision.daily_repository import (
    DailyExecutionConflictError,
    DailyExecutionRepository,
)
from decision.fixed_id_generator import FixedDecisionIdGenerator
from decision.production_composition import (
    ProductionDecisionRuntimeContainer,
    create_production_decision_runtime_application,
)
from decision.repository import DecisionAuditRecordRepository
from decision.runtime_workflow import DecisionClock, SystemUtcDecisionClock


@dataclass(frozen=True)
class CoordinatorExecutionResult:
    """Public result outcome returned by DailyDecisionRuntimeCoordinator."""
    outcome: DailyCoordinatorOutcome
    run_date_str: str
    decision_id: Optional[str]
    record: Optional[DailyExecutionRecord] = None


class DailyDecisionRuntimeCoordinator:
    """Orchestrates automated daily runtime runs with strictly at-most-once per local calendar day guarantees."""

    def __init__(
        self,
        daily_repository: DailyExecutionRepository,
        audit_repository: DecisionAuditRecordRepository,
        container_factory: Optional[Callable[[FixedDecisionIdGenerator], ProductionDecisionRuntimeContainer]] = None,
        clock: Optional[DecisionClock] = None,
        timezone_name: str = "Europe/Warsaw",
        lease_duration: timedelta = timedelta(minutes=15),
        id_factory: Optional[Callable[[], str]] = None,
    ) -> None:
        if daily_repository is None:
            raise TypeError("daily_repository must not be None")
        if audit_repository is None:
            raise TypeError("audit_repository must not be None")

        self._daily_repo = daily_repository
        self._audit_repo = audit_repository
        self._container_factory = container_factory or (
            lambda fixed_gen: create_production_decision_runtime_application(id_generator=fixed_gen)
        )
        self._clock = clock or SystemUtcDecisionClock()
        self._timezone_name = timezone_name
        self._lease_duration = lease_duration
        self._id_factory = id_factory or (lambda: f"decision-{uuid.uuid4()}")

    def run_daily_if_needed(self) -> CoordinatorExecutionResult:
        now_utc = self._clock.now()
        local_date = calculate_local_run_date(now_utc, self._timezone_name)
        date_str = local_date.isoformat()

        # 1. Check existing ledger state
        existing = self._daily_repo.get_by_run_date(local_date)

        if existing is not None:
            # 1a. Already COMPLETED
            if existing.status == DailyExecutionLedgerState.COMPLETED:
                return CoordinatorExecutionResult(
                    outcome=DailyCoordinatorOutcome.SKIPPED_ALREADY_COMPLETED,
                    run_date_str=date_str,
                    decision_id=existing.decision_id,
                    record=existing,
                )

            # 1b. Check if decision audit record already exists for reserved decision_id (CRASH RECOVERY)
            persisted_audit = self._audit_repo.get_by_id(existing.decision_id)
            if persisted_audit is not None:
                updated_rec = self._daily_repo.mark_completed(
                    run_date=local_date,
                    decision_id=existing.decision_id,
                    completed_at=now_utc,
                )
                return CoordinatorExecutionResult(
                    outcome=DailyCoordinatorOutcome.RECOVERED_COMPLETED,
                    run_date_str=date_str,
                    decision_id=existing.decision_id,
                    record=updated_rec,
                )

            # 1c. Currently RUNNING — check lease expiration
            if existing.status == DailyExecutionLedgerState.RUNNING:
                if existing.lease_expires_at is not None and now_utc < existing.lease_expires_at:
                    return CoordinatorExecutionResult(
                        outcome=DailyCoordinatorOutcome.SKIPPED_IN_PROGRESS,
                        run_date_str=date_str,
                        decision_id=existing.decision_id,
                        record=existing,
                    )

            # 1d. Expired RUNNING lease or FAILED status -> takeover retry reusing same decision_id
            reserved_id = existing.decision_id
            lease_exp = now_utc + self._lease_duration
            ledger_rec = self._daily_repo.takeover_retry(
                run_date=local_date,
                decision_id=reserved_id,
                new_started_at=now_utc,
                new_lease_expires_at=lease_exp,
            )
        else:
            # 2. First attempt for this date: reserve new decision_id
            reserved_id = self._id_factory()
            lease_exp = now_utc + self._lease_duration
            new_rec = DailyExecutionRecord(
                run_date=local_date,
                status=DailyExecutionLedgerState.RUNNING,
                decision_id=reserved_id,
                timezone_name=self._timezone_name,
                started_at=now_utc,
                lease_expires_at=lease_exp,
                attempt_count=1,
            )
            try:
                self._daily_repo.reserve(new_rec)
                ledger_rec = new_rec
            except DailyExecutionConflictError:
                # Concurrent process won reservation
                concurrent_rec = self._daily_repo.get_by_run_date(local_date)
                if concurrent_rec and concurrent_rec.status == DailyExecutionLedgerState.COMPLETED:
                    return CoordinatorExecutionResult(
                        outcome=DailyCoordinatorOutcome.SKIPPED_ALREADY_COMPLETED,
                        run_date_str=date_str,
                        decision_id=concurrent_rec.decision_id,
                        record=concurrent_rec,
                    )
                return CoordinatorExecutionResult(
                    outcome=DailyCoordinatorOutcome.SKIPPED_IN_PROGRESS,
                    run_date_str=date_str,
                    decision_id=concurrent_rec.decision_id if concurrent_rec else reserved_id,
                    record=concurrent_rec,
                )

        # 3. Execute Production Decision Runtime using FixedDecisionIdGenerator
        fixed_gen = FixedDecisionIdGenerator(reserved_id)
        try:
            with self._container_factory(fixed_gen) as container:
                result = container.app.workflow.run()
                exec_record = result.record

            # Double check audit repository to confirm persistence
            audit_confirm = self._audit_repo.get_by_id(reserved_id)
            if audit_confirm is None:
                # Safety check if audit save failed unexpectedly
                updated_fail = self._daily_repo.mark_failed(
                    run_date=local_date,
                    error_message="Decision audit record missing after execution",
                    completed_at=self._clock.now(),
                )
                return CoordinatorExecutionResult(
                    outcome=DailyCoordinatorOutcome.FAILED,
                    run_date_str=date_str,
                    decision_id=reserved_id,
                    record=updated_fail,
                )

            final_rec = self._daily_repo.mark_completed(
                run_date=local_date,
                decision_id=reserved_id,
                completed_at=self._clock.now(),
            )
            return CoordinatorExecutionResult(
                outcome=DailyCoordinatorOutcome.EXECUTED,
                run_date_str=date_str,
                decision_id=reserved_id,
                record=final_rec,
            )

        except Exception as err:
            # Check if audit repository actually succeeded despite exception (Failure Race Defense)
            audit_check = self._audit_repo.get_by_id(reserved_id)
            if audit_check is not None:
                updated_rec = self._daily_repo.mark_completed(
                    run_date=local_date,
                    decision_id=reserved_id,
                    completed_at=self._clock.now(),
                )
                return CoordinatorExecutionResult(
                    outcome=DailyCoordinatorOutcome.RECOVERED_COMPLETED,
                    run_date_str=date_str,
                    decision_id=reserved_id,
                    record=updated_rec,
                )

            err_msg = f"{type(err).__name__}: {str(err)}"
            updated_fail = self._daily_repo.mark_failed(
                run_date=local_date,
                error_message=err_msg[:250],
                completed_at=self._clock.now(),
            )
            return CoordinatorExecutionResult(
                outcome=DailyCoordinatorOutcome.FAILED,
                run_date_str=date_str,
                decision_id=reserved_id,
                record=updated_fail,
            )
