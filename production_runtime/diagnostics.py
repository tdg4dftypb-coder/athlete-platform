"""Read-only operational diagnostics projected from persisted runtime audits."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum

from production_runtime.clock import RuntimeClock, SystemUtcRuntimeClock
from production_runtime.models import (
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimeFailure,
    RuntimePhase,
    RuntimeStatus,
    RuntimeWarning,
    SourceWatermark,
)
from production_runtime.repository import RuntimeAuditRepository


class RuntimeOperationalHealth(str, Enum):
    NO_DATA = "no_data"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    FAILED = "failed"


class RuntimeResumability(str, Enum):
    RESUME_SAME_ATTEMPT = "resume_same_attempt"
    START_NEW_ATTEMPT = "start_new_attempt"
    NO_ACTION = "no_action"
    NOT_SUPPORTED = "not_supported"


@dataclass(frozen=True)
class RuntimePhaseDiagnostic:
    phase: RuntimePhase
    present: bool
    status: PhaseStatus | None = None
    started_at_utc: datetime | None = None
    completed_at_utc: datetime | None = None
    changed_state: bool | None = None
    item_count: int | None = None
    artifact_ids: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeCounterDiagnostic:
    activities_discovered: int | None
    activity_facts_created: int | None
    activities_already_present: int | None
    reconciliations_created: int | None


@dataclass(frozen=True)
class RuntimeArtifactReferences:
    decision_id: str | None
    training_plan_id: str | None
    prescription_id: str | None
    morning_briefing_available: bool


@dataclass(frozen=True)
class RuntimeOperationalSnapshot:
    runtime_id: str
    logical_execution_key: str
    target_local_date: date
    contract_version: str
    revision: int
    status: RuntimeStatus
    health: RuntimeOperationalHealth
    started_at_utc: datetime
    completed_at_utc: datetime | None
    last_durable_progress_at_utc: datetime
    stale_running: bool
    resumability: RuntimeResumability
    next_expected_phase: RuntimePhase | None
    phases: tuple[RuntimePhaseDiagnostic, ...]
    failure: RuntimeFailure | None
    warnings: tuple[RuntimeWarning, ...]
    source_watermarks: tuple[SourceWatermark, ...]
    counters: RuntimeCounterDiagnostic
    artifact_references: RuntimeArtifactReferences


class RuntimeOperationalStatusReader:
    """Projects immutable audit records without mutating or executing a runtime."""

    DEFAULT_STALE_AFTER = timedelta(minutes=30)

    def __init__(
        self,
        repository: RuntimeAuditRepository,
        clock: RuntimeClock | None = None,
        stale_after: timedelta = DEFAULT_STALE_AFTER,
    ) -> None:
        if stale_after <= timedelta(0):
            raise ValueError("stale_after must be positive")
        self._repository = repository
        self._clock = clock or SystemUtcRuntimeClock()
        self._stale_after = stale_after

    def get_latest(self) -> RuntimeOperationalSnapshot | None:
        record = self._repository.get_latest()
        return None if record is None else self._project(record)

    def get_latest_for_date(self, target_date: date) -> RuntimeOperationalSnapshot | None:
        attempts = self._repository.list_for_target_date(target_date)
        return None if not attempts else self._project(attempts[-1])

    def list_for_date(self, target_date: date) -> tuple[RuntimeOperationalSnapshot, ...]:
        return tuple(
            self._project(record)
            for record in self._repository.list_for_target_date(target_date)
        )

    def get_by_runtime_id(self, runtime_id: str) -> RuntimeOperationalSnapshot | None:
        record = self._repository.get_by_runtime_id(runtime_id)
        return None if record is None else self._project(record)

    def _project(self, record: ProductionDailyRuntimeResult) -> RuntimeOperationalSnapshot:
        last_progress = self._last_durable_progress(record)
        now = self._clock.now_utc()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("runtime diagnostics clock must return a timezone-aware UTC datetime")
        if now.utcoffset() != timezone.utc.utcoffset(now):
            raise ValueError("runtime diagnostics clock must return UTC")
        stale = (
            record.status is RuntimeStatus.RUNNING
            and now - last_progress > self._stale_after
        )
        phase_by_name = {item.phase: item for item in record.phases}
        phases = tuple(
            RuntimePhaseDiagnostic(
                phase=phase,
                present=phase in phase_by_name,
                status=phase_by_name[phase].status if phase in phase_by_name else None,
                started_at_utc=(phase_by_name[phase].started_at_utc if phase in phase_by_name else None),
                completed_at_utc=(phase_by_name[phase].completed_at_utc if phase in phase_by_name else None),
                changed_state=(phase_by_name[phase].changed_state if phase in phase_by_name else None),
                item_count=phase_by_name[phase].item_count if phase in phase_by_name else None,
                artifact_ids=phase_by_name[phase].artifact_ids if phase in phase_by_name else (),
                warning_codes=phase_by_name[phase].warning_codes if phase in phase_by_name else (),
            )
            for phase in RuntimePhase
        )
        return RuntimeOperationalSnapshot(
            runtime_id=record.runtime_id,
            logical_execution_key=record.logical_execution_key,
            target_local_date=record.target_local_date,
            contract_version=record.contract_version,
            revision=record.revision,
            status=record.status,
            health=self._health(record, stale),
            started_at_utc=record.started_at_utc,
            completed_at_utc=record.completed_at_utc,
            last_durable_progress_at_utc=last_progress,
            stale_running=stale,
            resumability=self._resumability(record),
            next_expected_phase=self._next_expected_phase(record),
            phases=phases,
            failure=record.failure,
            warnings=record.warnings,
            source_watermarks=record.source_watermarks,
            counters=RuntimeCounterDiagnostic(
                record.activities_discovered,
                record.activity_facts_created,
                record.activities_already_present,
                record.reconciliations_created,
            ),
            artifact_references=RuntimeArtifactReferences(
                record.decision_id,
                record.training_plan_id,
                record.prescription_id,
                record.morning_briefing_available,
            ),
        )

    @staticmethod
    def _last_durable_progress(record: ProductionDailyRuntimeResult) -> datetime:
        candidates = [record.started_at_utc]
        if record.completed_at_utc is not None:
            candidates.append(record.completed_at_utc)
        candidates.extend(item.completed_at_utc for item in record.phases)
        return max(candidates)

    @staticmethod
    def _health(
        record: ProductionDailyRuntimeResult,
        stale: bool,
    ) -> RuntimeOperationalHealth:
        if stale:
            return RuntimeOperationalHealth.STALE
        if record.status is RuntimeStatus.FAILED:
            return RuntimeOperationalHealth.FAILED
        if record.failure is not None or any(
            item.status is PhaseStatus.FAILED for item in record.phases
        ):
            return RuntimeOperationalHealth.DEGRADED
        return RuntimeOperationalHealth.HEALTHY

    @staticmethod
    def _resumability(record: ProductionDailyRuntimeResult) -> RuntimeResumability:
        if record.status is RuntimeStatus.COMPLETED:
            return RuntimeResumability.NO_ACTION
        if record.status in (RuntimeStatus.PARTIAL, RuntimeStatus.FAILED):
            return RuntimeResumability.START_NEW_ATTEMPT
        phases = tuple(item.phase for item in record.phases)
        if phases in ((), (RuntimePhase.INGESTION,)):
            return RuntimeResumability.RESUME_SAME_ATTEMPT
        return RuntimeResumability.NOT_SUPPORTED

    @staticmethod
    def _next_expected_phase(record: ProductionDailyRuntimeResult) -> RuntimePhase | None:
        if record.status is RuntimeStatus.COMPLETED:
            return None
        present = {item.phase for item in record.phases}
        return next((phase for phase in RuntimePhase if phase not in present), None)
