"""Authoritative application coordinator for one production daily runtime attempt."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Callable, Mapping, Protocol
from uuid import uuid4

import duckdb

from production_runtime.clock import RuntimeClock, SystemUtcRuntimeClock
from production_runtime.models import (
    RUNTIME_CONTRACT_VERSION,
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimeFailure,
    RuntimePhase,
    RuntimePhaseResult,
    RuntimeStatus,
    RuntimeWarning,
    SourceWatermark,
    logical_execution_key,
)
from production_runtime.repository import RuntimeAuditRepository


PHASE_INTERRUPTED = "phase_interrupted"
PERSISTENCE_UNAVAILABLE = "persistence_unavailable"
MISSING_TRAINING_PLAN = "missing_training_plan"
PHASE_NOT_RESUMABLE = "phase_not_resumable"
RECONCILIATION_NOT_APPLICABLE = "reconciliation_not_applicable"


class RuntimeAttemptNotResumableError(RuntimeError):
    """Raised when same-attempt continuation would violate immutable history."""


class RuntimePhaseError(RuntimeError):
    """Stable, bounded failure raised by a phase adapter."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class RuntimePhaseContext:
    """Frozen attempt identity plus previously persisted operational state."""

    result: ProductionDailyRuntimeResult

    @property
    def target_local_date(self) -> date:
        return self.result.target_local_date


@dataclass(frozen=True)
class RuntimePhaseOutcome:
    """Bounded domain-to-runtime translation returned by phase adapters."""

    status: PhaseStatus = PhaseStatus.COMPLETED
    changed_state: bool = False
    item_count: int | None = None
    artifact_ids: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()
    warnings: tuple[RuntimeWarning, ...] = ()
    source_watermarks: tuple[SourceWatermark, ...] = ()
    decision_id: str | None = None
    training_plan_id: str | None = None
    prescription_id: str | None = None
    morning_briefing_available: bool | None = None
    activities_discovered: int | None = None
    activity_facts_created: int | None = None
    activities_already_present: int | None = None
    reconciliations_created: int | None = None


class RuntimePhaseAdapter(Protocol):
    def execute(self, context: RuntimePhaseContext) -> RuntimePhaseOutcome: ...


class ProductionDailyRuntime:
    """Orders existing capabilities and appends one revision after every phase."""

    def __init__(
        self,
        audit_repository: RuntimeAuditRepository,
        phase_adapters: Mapping[RuntimePhase, RuntimePhaseAdapter],
        clock: RuntimeClock | None = None,
        runtime_id_factory: Callable[[], str] | None = None,
        timezone_name: str = "Europe/Warsaw",
    ) -> None:
        self._audit = audit_repository
        self._adapters = dict(phase_adapters)
        missing = tuple(phase for phase in RuntimePhase if phase not in self._adapters)
        if missing:
            raise ValueError(f"Missing runtime phase adapters: {', '.join(p.value for p in missing)}")
        self._clock = clock or SystemUtcRuntimeClock()
        self._runtime_id_factory = runtime_id_factory or (lambda: f"runtime-{uuid4()}")
        self._timezone_name = timezone_name

    def run_new_attempt(self, target_local_date: date) -> ProductionDailyRuntimeResult:
        if type(target_local_date) is not date:
            raise TypeError("target_local_date must be a date")
        started_at = self._clock.now_utc()
        current = ProductionDailyRuntimeResult(
            runtime_id=self._runtime_id_factory(),
            logical_execution_key=logical_execution_key(target_local_date),
            revision=1,
            contract_version=RUNTIME_CONTRACT_VERSION,
            target_local_date=target_local_date,
            timezone_name=self._timezone_name,
            started_at_utc=started_at,
            completed_at_utc=None,
            status=RuntimeStatus.RUNNING,
        )
        self._audit.append(current)
        return self._continue(current)

    def resume_attempt(self, runtime_id: str) -> ProductionDailyRuntimeResult:
        current = self._audit.get_by_runtime_id(runtime_id)
        if current is None:
            raise ValueError(f"Unknown runtime_id '{runtime_id}'")
        if current.status is not RuntimeStatus.RUNNING:
            raise RuntimeAttemptNotResumableError(
                f"Runtime attempt '{runtime_id}' is terminal with status {current.status.value}"
            )
        completed = {item.phase for item in current.phases}
        snapshot_lost = (
            RuntimePhase.ASSESSMENT in completed
            and RuntimePhase.MORNING_BRIEFING not in completed
        )
        if snapshot_lost:
            raise RuntimeAttemptNotResumableError(
                f"{PHASE_NOT_RESUMABLE}: immutable assessment snapshot is not persisted"
            )
        return self._continue(current)

    def _continue(self, current: ProductionDailyRuntimeResult) -> ProductionDailyRuntimeResult:
        persisted = {phase.phase for phase in current.phases}
        for phase in RuntimePhase:
            if phase in persisted:
                continue
            started_at = self._clock.now_utc()
            try:
                outcome = self._adapters[phase].execute(RuntimePhaseContext(current))
                if outcome.status is PhaseStatus.FAILED:
                    raise RuntimePhaseError(
                        outcome.warning_codes[0] if outcome.warning_codes else PHASE_INTERRUPTED
                    )
                phase_result = RuntimePhaseResult(
                    phase=phase,
                    status=outcome.status,
                    started_at_utc=started_at,
                    completed_at_utc=self._clock.now_utc(),
                    changed_state=outcome.changed_state,
                    item_count=outcome.item_count,
                    artifact_ids=outcome.artifact_ids,
                    warning_codes=outcome.warning_codes,
                )
                current = self._append_phase(current, phase_result, outcome)
            except Exception as error:
                return self._terminate(current, phase, started_at, error)

        if not self._completion_invariant(current):
            return self._terminate(
                current,
                RuntimePhase.PUBLICATION,
                self._clock.now_utc(),
                RuntimePhaseError("completion_invariant_failed"),
                append_phase=False,
            )
        completed = replace(
            current,
            revision=current.revision + 1,
            status=RuntimeStatus.COMPLETED,
            completed_at_utc=self._clock.now_utc(),
        )
        self._audit.append(completed, expected_revision=current.revision)
        return completed

    def _append_phase(
        self,
        current: ProductionDailyRuntimeResult,
        phase: RuntimePhaseResult,
        outcome: RuntimePhaseOutcome,
    ) -> ProductionDailyRuntimeResult:
        values = {
            "revision": current.revision + 1,
            "phases": current.phases + (phase,),
            "warnings": current.warnings + outcome.warnings,
            "source_watermarks": current.source_watermarks + outcome.source_watermarks,
        }
        for name in (
            "decision_id", "training_plan_id", "prescription_id",
            "activities_discovered", "activity_facts_created",
            "activities_already_present", "reconciliations_created",
        ):
            value = getattr(outcome, name)
            if value is not None:
                values[name] = value
        if outcome.morning_briefing_available is not None:
            values["morning_briefing_available"] = outcome.morning_briefing_available
        updated = replace(current, **values)
        self._audit.append(updated, expected_revision=current.revision)
        return updated

    def _terminate(
        self,
        current: ProductionDailyRuntimeResult,
        phase: RuntimePhase,
        started_at,
        error: Exception,
        append_phase: bool = True,
    ) -> ProductionDailyRuntimeResult:
        code = self._failure_code(error)
        now = self._clock.now_utc()
        phases = current.phases
        if append_phase:
            phases += (RuntimePhaseResult(
                phase=phase,
                status=PhaseStatus.FAILED,
                started_at_utc=started_at,
                completed_at_utc=now,
                changed_state=False,
                warning_codes=(code,),
            ),)
        terminal = replace(
            current,
            revision=current.revision + 1,
            status=RuntimeStatus.PARTIAL if current.phases else RuntimeStatus.FAILED,
            completed_at_utc=now,
            phases=phases,
            warnings=current.warnings + (RuntimeWarning(code, self._bounded_detail(error), phase.value),),
            failure=RuntimeFailure(code, phase, self._bounded_detail(error)),
        )
        self._audit.append(terminal, expected_revision=current.revision)
        return terminal

    @staticmethod
    def _completion_invariant(result: ProductionDailyRuntimeResult) -> bool:
        phases = {item.phase: item for item in result.phases}
        return (
            tuple(item.phase for item in result.phases) == tuple(RuntimePhase)
            and all(item.status in (PhaseStatus.COMPLETED, PhaseStatus.SKIPPED) for item in phases.values())
            and all(
                item.status is not PhaseStatus.SKIPPED
                or item.phase is RuntimePhase.RECONCILIATION
                for item in phases.values()
            )
            and result.decision_id is not None
            and result.training_plan_id is not None
            and result.prescription_id is not None
            and result.morning_briefing_available
            and phases[RuntimePhase.PUBLICATION].status is PhaseStatus.COMPLETED
            and result.failure is None
        )

    @staticmethod
    def _failure_code(error: Exception) -> str:
        if isinstance(error, RuntimePhaseError):
            return error.code
        if isinstance(error, duckdb.Error):
            return PERSISTENCE_UNAVAILABLE
        return PHASE_INTERRUPTED

    @staticmethod
    def _bounded_detail(error: Exception) -> str:
        detail = getattr(error, "detail", None) or f"{type(error).__name__}: {error}"
        return str(detail).strip()[:200] or type(error).__name__
