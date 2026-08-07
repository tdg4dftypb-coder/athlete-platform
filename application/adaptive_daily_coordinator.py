"""Application-level adaptive daily runtime coordinator and outcome contracts."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from application.training_plan_decision_context import MissingTrainingPlanError
from application.training_plan_reconciliation import DailyTrainingReconciler
from decision.daily_coordinator import (
    CoordinatorExecutionResult,
    DailyDecisionRuntimeCoordinator,
)
from decision.daily_execution import DailyCoordinatorOutcome
from decision.repository import DecisionAuditRecordRepository
from training_plan.prescription import FinalSessionPrescription
from training_plan.repository import (
    FinalSessionPrescriptionRepository,
    TrainingPlanRepository,
    TrainingPlanRepositoryError,
)


class AdaptiveDailyRuntimeOutcome(str, Enum):
    EXECUTED = "executed"
    SKIPPED_ALREADY_COMPLETED = "skipped_already_completed"
    SKIPPED_IN_PROGRESS = "skipped_in_progress"
    RECOVERED_COMPLETED = "recovered_completed"
    MISSING_PLAN = "missing_plan"
    FAILED = "failed"


@dataclass(frozen=True)
class AdaptiveDailyRuntimeResult:
    """Result payload of an AdaptiveDailyRuntimeCoordinator run."""

    outcome: AdaptiveDailyRuntimeOutcome
    run_date_str: str
    decision_id: Optional[str] = None
    prescription_id: Optional[str] = None
    inner_outcome: Optional[DailyCoordinatorOutcome] = None


class AdaptiveDailyRuntimeCoordinator:
    """Coordinates outer Stage 26 adaptive daily workflow around Stage 25 DailyDecisionRuntimeCoordinator."""

    def __init__(
        self,
        decision_coordinator: DailyDecisionRuntimeCoordinator,
        decision_audit_repository: DecisionAuditRecordRepository,
        training_plan_repository: TrainingPlanRepository,
        prescription_repository: FinalSessionPrescriptionRepository,
        reconciler: DailyTrainingReconciler | None = None,
    ) -> None:
        if decision_coordinator is None:
            raise TypeError("decision_coordinator must not be None")
        if decision_audit_repository is None:
            raise TypeError("decision_audit_repository must not be None")
        if training_plan_repository is None:
            raise TypeError("training_plan_repository must not be None")
        if prescription_repository is None:
            raise TypeError("prescription_repository must not be None")

        self._decision_coordinator = decision_coordinator
        self._audit_repo = decision_audit_repository
        self._tp_repo = training_plan_repository
        self._rx_repo = prescription_repository
        self._reconciler = reconciler or DailyTrainingReconciler()

    def run_adaptive_daily(self) -> AdaptiveDailyRuntimeResult:
        # 1. Pre-check TrainingPlan existence for current run date BEFORE making daily decision reservation
        now_utc = self._decision_coordinator._clock.now()
        from decision.daily_execution import calculate_local_run_date
        local_d = calculate_local_run_date(now_utc, self._decision_coordinator._timezone_name)

        try:
            from training_plan.provider import RepositoryTrainingPlanProvider
            provider = RepositoryTrainingPlanProvider(self._tp_repo)
            plan_snapshot = provider.get_plan_for_date(local_d)
        except Exception:
            plan_snapshot = None

        if plan_snapshot is None:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.MISSING_PLAN,
                run_date_str=local_d.isoformat(),
            )

        # 2. Delegate to inner Stage 25 decision coordinator
        try:
            decision_res: CoordinatorExecutionResult = self._decision_coordinator.run_daily_if_needed()
        except MissingTrainingPlanError:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.MISSING_PLAN,
                run_date_str=local_d.isoformat(),
            )
        except Exception:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=local_d.isoformat(),
            )

        date_str = decision_res.run_date_str
        decision_id = decision_res.decision_id
        inner_outcome = decision_res.outcome

        if inner_outcome == DailyCoordinatorOutcome.SKIPPED_IN_PROGRESS:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.SKIPPED_IN_PROGRESS,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        if inner_outcome == DailyCoordinatorOutcome.FAILED or decision_id is None:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        # 2. Retrieve persisted DecisionAuditRecord
        dec_record = self._audit_repo.get_by_id(decision_id)
        if dec_record is None:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        # 3. Check legacy record compatibility (provenance requirement)
        plan_id = dec_record.context.training.plan_id
        planned_session_id = dec_record.context.training.planned_session_id

        if not plan_id or not planned_session_id:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        # 4. Check if matching FinalSessionPrescription already exists
        target_rx_id = f"{planned_session_id}:{decision_id}"
        existing_rx = self._rx_repo.get_by_id(target_rx_id)

        if existing_rx is not None:
            final_outcome = (
                AdaptiveDailyRuntimeOutcome.SKIPPED_ALREADY_COMPLETED
                if inner_outcome == DailyCoordinatorOutcome.SKIPPED_ALREADY_COMPLETED
                else (
                    AdaptiveDailyRuntimeOutcome.RECOVERED_COMPLETED
                    if inner_outcome == DailyCoordinatorOutcome.RECOVERED_COMPLETED
                    else AdaptiveDailyRuntimeOutcome.EXECUTED
                )
            )
            return AdaptiveDailyRuntimeResult(
                outcome=final_outcome,
                run_date_str=date_str,
                decision_id=decision_id,
                prescription_id=existing_rx.prescription_id,
                inner_outcome=inner_outcome,
            )

        # 5. Reconstruct exact historical PlannedSession from DecisionAuditRecord provenance
        try:
            source_plan = self._tp_repo.get_by_id(plan_id)
        except TrainingPlanRepositoryError:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        if source_plan is None:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        source_session = None
        for s in source_plan.sessions:
            if s.session_id == planned_session_id:
                source_session = s
                break

        if source_session is None:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        # 6. Reconcile exact source session with DecisionAuditRecord
        try:
            prescription: FinalSessionPrescription = self._reconciler.reconcile(
                plan_id=source_plan.plan_id,
                planned_session=source_session,
                decision_record=dec_record,
            )
            self._rx_repo.save(prescription)
        except Exception:
            return AdaptiveDailyRuntimeResult(
                outcome=AdaptiveDailyRuntimeOutcome.FAILED,
                run_date_str=date_str,
                decision_id=decision_id,
                inner_outcome=inner_outcome,
            )

        final_outcome = (
            AdaptiveDailyRuntimeOutcome.RECOVERED_COMPLETED
            if inner_outcome in (DailyCoordinatorOutcome.RECOVERED_COMPLETED, DailyCoordinatorOutcome.SKIPPED_ALREADY_COMPLETED)
            else AdaptiveDailyRuntimeOutcome.EXECUTED
        )

        return AdaptiveDailyRuntimeResult(
            outcome=final_outcome,
            run_date_str=date_str,
            decision_id=decision_id,
            prescription_id=prescription.prescription_id,
            inner_outcome=inner_outcome,
        )
