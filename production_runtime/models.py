"""Immutable operational audit contract for production daily runtime attempts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum


RUNTIME_CONTRACT_VERSION = "1.0"


class RuntimeStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class RuntimePhase(str, Enum):
    INGESTION = "ingestion"
    ACTIVITY_FACT_SYNCHRONIZATION = "activity_fact_synchronization"
    RECONCILIATION = "reconciliation"
    ASSESSMENT = "assessment"
    DECISION = "decision"
    PLAN_PRESCRIPTION = "plan_prescription"
    PLAN_HORIZON_CONTINUITY = "plan_horizon_continuity"
    PLAN_ADAPTATION = "plan_adaptation"
    MORNING_BRIEFING = "morning_briefing"
    PUBLICATION = "publication"


class PhaseStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


def _non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _aware_utc(value: datetime, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must use UTC")


def _string_tuple(value: tuple[str, ...], field_name: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    for item in value:
        _non_empty(item, f"{field_name} item")


def logical_execution_key(target_local_date: date, contract_version: str = RUNTIME_CONTRACT_VERSION) -> str:
    """Build the stable logical-day key shared by independent runtime attempts."""
    if type(target_local_date) is not date:
        raise TypeError("target_local_date must be a date")
    _non_empty(contract_version, "contract_version")
    return f"{target_local_date.isoformat()}:{contract_version}"


@dataclass(frozen=True)
class RuntimeWarning:
    code: str
    detail: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.code, "warning code")
        if self.detail is not None:
            _non_empty(self.detail, "warning detail")
        if self.source is not None:
            _non_empty(self.source, "warning source")


@dataclass(frozen=True)
class RuntimeFailure:
    code: str
    phase: RuntimePhase | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.code, "failure code")
        if self.phase is not None and not isinstance(self.phase, RuntimePhase):
            raise TypeError("failure phase must be RuntimePhase or None")
        if self.detail is not None:
            _non_empty(self.detail, "failure detail")


@dataclass(frozen=True)
class SourceWatermark:
    source: str
    kind: str
    value: str
    observed_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        _non_empty(self.source, "watermark source")
        _non_empty(self.kind, "watermark kind")
        _non_empty(self.value, "watermark value")
        if self.observed_at_utc is not None:
            _aware_utc(self.observed_at_utc, "observed_at_utc")


@dataclass(frozen=True)
class RuntimePhaseResult:
    phase: RuntimePhase
    status: PhaseStatus
    started_at_utc: datetime
    completed_at_utc: datetime
    changed_state: bool
    item_count: int | None = None
    artifact_ids: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.phase, RuntimePhase):
            raise TypeError("phase must be RuntimePhase")
        if not isinstance(self.status, PhaseStatus):
            raise TypeError("status must be PhaseStatus")
        _aware_utc(self.started_at_utc, "started_at_utc")
        _aware_utc(self.completed_at_utc, "completed_at_utc")
        if self.completed_at_utc < self.started_at_utc:
            raise ValueError("phase completed_at_utc cannot precede started_at_utc")
        if not isinstance(self.changed_state, bool):
            raise TypeError("changed_state must be bool")
        if self.item_count is not None and (not isinstance(self.item_count, int) or self.item_count < 0):
            raise ValueError("item_count must be a non-negative int or None")
        _string_tuple(self.artifact_ids, "artifact_ids")
        _string_tuple(self.warning_codes, "warning_codes")
        if len(set(self.artifact_ids)) != len(self.artifact_ids):
            raise ValueError("artifact_ids must not contain duplicates")
        if len(set(self.warning_codes)) != len(self.warning_codes):
            raise ValueError("warning_codes must not contain duplicates")


@dataclass(frozen=True)
class ProductionDailyRuntimeResult:
    runtime_id: str
    logical_execution_key: str
    revision: int
    contract_version: str
    target_local_date: date
    timezone_name: str
    started_at_utc: datetime
    completed_at_utc: datetime | None
    status: RuntimeStatus
    phases: tuple[RuntimePhaseResult, ...] = ()
    decision_id: str | None = None
    training_plan_id: str | None = None
    prescription_id: str | None = None
    morning_briefing_available: bool = False
    activities_discovered: int | None = None
    activity_facts_created: int | None = None
    activities_already_present: int | None = None
    reconciliations_created: int | None = None
    source_watermarks: tuple[SourceWatermark, ...] = ()
    warnings: tuple[RuntimeWarning, ...] = ()
    failure: RuntimeFailure | None = None

    def __post_init__(self) -> None:
        _non_empty(self.runtime_id, "runtime_id")
        _non_empty(self.logical_execution_key, "logical_execution_key")
        _non_empty(self.contract_version, "contract_version")
        _non_empty(self.timezone_name, "timezone_name")
        if self.contract_version != RUNTIME_CONTRACT_VERSION:
            raise ValueError(f"unsupported contract_version '{self.contract_version}'")
        if type(self.target_local_date) is not date:
            raise TypeError("target_local_date must be a date")
        expected_key = logical_execution_key(self.target_local_date, self.contract_version)
        if self.logical_execution_key != expected_key:
            raise ValueError("logical_execution_key does not match target date and contract version")
        if not isinstance(self.revision, int) or self.revision < 1:
            raise ValueError("revision must be an int >= 1")
        _aware_utc(self.started_at_utc, "started_at_utc")
        if self.completed_at_utc is not None:
            _aware_utc(self.completed_at_utc, "completed_at_utc")
            if self.completed_at_utc < self.started_at_utc:
                raise ValueError("completed_at_utc cannot precede started_at_utc")
        if not isinstance(self.status, RuntimeStatus):
            raise TypeError("status must be RuntimeStatus")
        if not isinstance(self.phases, tuple):
            raise TypeError("phases must be a tuple")
        if any(not isinstance(item, RuntimePhaseResult) for item in self.phases):
            raise TypeError("phases items must be RuntimePhaseResult")
        phase_names = tuple(item.phase for item in self.phases)
        if len(set(phase_names)) != len(phase_names):
            raise ValueError("phases must not contain duplicate phase entries")
        for field_name in ("decision_id", "training_plan_id", "prescription_id"):
            value = getattr(self, field_name)
            if value is not None:
                _non_empty(value, field_name)
        if not isinstance(self.morning_briefing_available, bool):
            raise TypeError("morning_briefing_available must be bool")
        for field_name in (
            "activities_discovered",
            "activity_facts_created",
            "activities_already_present",
            "reconciliations_created",
        ):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"{field_name} must be a non-negative int or None")
        if not isinstance(self.source_watermarks, tuple) or any(
            not isinstance(item, SourceWatermark) for item in self.source_watermarks
        ):
            raise TypeError("source_watermarks must be a tuple of SourceWatermark")
        if not isinstance(self.warnings, tuple) or any(
            not isinstance(item, RuntimeWarning) for item in self.warnings
        ):
            raise TypeError("warnings must be a tuple of RuntimeWarning")
        if self.failure is not None and not isinstance(self.failure, RuntimeFailure):
            raise TypeError("failure must be RuntimeFailure or None")
        if self.status is RuntimeStatus.RUNNING:
            if self.completed_at_utc is not None or self.failure is not None:
                raise ValueError("RUNNING runtime cannot be completed or failed")
        else:
            if self.completed_at_utc is None:
                raise ValueError("terminal runtime status requires completed_at_utc")
        if self.status is RuntimeStatus.COMPLETED:
            if self.failure is not None or any(p.status is PhaseStatus.FAILED for p in self.phases):
                raise ValueError("COMPLETED runtime cannot contain failure data")
        if self.status is RuntimeStatus.FAILED and self.failure is None:
            raise ValueError("FAILED runtime requires failure data")
