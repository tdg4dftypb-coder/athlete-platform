from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone

import pytest

from production_runtime import (
    RUNTIME_CONTRACT_VERSION,
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimeFailure,
    RuntimePhase,
    RuntimePhaseResult,
    RuntimeStatus,
    RuntimeWarning,
    SourceWatermark,
    SystemUtcRuntimeClock,
    logical_execution_key,
    target_local_date_at,
)


START = datetime(2026, 8, 10, 22, 30, tzinfo=timezone.utc)
TARGET = date(2026, 8, 11)


def running_result(**changes) -> ProductionDailyRuntimeResult:
    values = {
        "runtime_id": "runtime-001",
        "logical_execution_key": logical_execution_key(TARGET),
        "revision": 1,
        "contract_version": RUNTIME_CONTRACT_VERSION,
        "target_local_date": TARGET,
        "timezone_name": "Europe/Warsaw",
        "started_at_utc": START,
        "completed_at_utc": None,
        "status": RuntimeStatus.RUNNING,
    }
    values.update(changes)
    return ProductionDailyRuntimeResult(**values)


def test_runtime_contract_is_frozen_and_keeps_target_date_independent_of_start() -> None:
    result = running_result()
    assert result.target_local_date == TARGET
    assert result.started_at_utc == START
    with pytest.raises(FrozenInstanceError):
        result.status = RuntimeStatus.COMPLETED


def test_logical_execution_key_is_stable_and_validated() -> None:
    assert logical_execution_key(TARGET) == "2026-08-11:1.0"
    with pytest.raises(ValueError, match="logical_execution_key"):
        running_result(logical_execution_key="wrong")


def test_phase_result_supports_operational_metadata() -> None:
    result = RuntimePhaseResult(
        phase=RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION,
        status=PhaseStatus.COMPLETED,
        started_at_utc=START,
        completed_at_utc=START + timedelta(seconds=2),
        changed_state=True,
        item_count=2,
        artifact_ids=("activity-1", "activity-2"),
        warning_codes=("STALE_INPUT",),
    )
    assert result.item_count == 2
    assert result.changed_state is True


@pytest.mark.parametrize("field_name", ["started_at_utc", "completed_at_utc"])
def test_phase_timestamps_must_be_aware_utc(field_name: str) -> None:
    values = {
        "phase": RuntimePhase.INGESTION,
        "status": PhaseStatus.COMPLETED,
        "started_at_utc": START,
        "completed_at_utc": START,
        "changed_state": False,
    }
    values[field_name] = datetime(2026, 8, 10, 22, 30)
    with pytest.raises(ValueError, match="timezone-aware"):
        RuntimePhaseResult(**values)


def test_warning_failure_and_generic_watermark_are_operational() -> None:
    warning = RuntimeWarning("OPTIONAL_SOURCE_UNAVAILABLE", "Garmin unavailable", "activity")
    failure = RuntimeFailure("DATABASE_LOCKED", RuntimePhase.DECISION, "retry later")
    watermark = SourceWatermark("health", "max_local_date", "2026-08-10", START)
    result = running_result(warnings=(warning,), source_watermarks=(watermark,))
    assert result.warnings == (warning,)
    assert failure.phase is RuntimePhase.DECISION


def test_optional_counters_and_domain_references_are_not_fabricated() -> None:
    result = running_result()
    assert result.decision_id is None
    assert result.activities_discovered is None
    with pytest.raises(ValueError, match="activities_discovered"):
        running_result(activities_discovered=-1)


def test_running_and_terminal_status_invariants() -> None:
    with pytest.raises(ValueError, match="RUNNING"):
        running_result(completed_at_utc=START)
    with pytest.raises(ValueError, match="requires completed_at_utc"):
        running_result(status=RuntimeStatus.PARTIAL)
    with pytest.raises(ValueError, match="requires failure"):
        running_result(status=RuntimeStatus.FAILED, completed_at_utc=START)


def test_completed_cannot_contain_failed_phase() -> None:
    phase = RuntimePhaseResult(
        RuntimePhase.PUBLICATION,
        PhaseStatus.FAILED,
        START,
        START,
        False,
    )
    with pytest.raises(ValueError, match="COMPLETED"):
        running_result(
            status=RuntimeStatus.COMPLETED,
            completed_at_utc=START,
            phases=(phase,),
        )


def test_target_date_boundary_handles_warsaw_midnight_once() -> None:
    before = datetime(2026, 8, 10, 21, 59, tzinfo=timezone.utc)
    after = datetime(2026, 8, 10, 22, 0, tzinfo=timezone.utc)
    assert target_local_date_at(before) == date(2026, 8, 10)
    assert target_local_date_at(after) == date(2026, 8, 11)


def test_clock_protocol_returns_aware_utc() -> None:
    instant = SystemUtcRuntimeClock().now_utc()
    assert instant.tzinfo is not None
    assert instant.utcoffset() == timedelta(0)


def test_target_date_requires_utc_instant() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        target_local_date_at(datetime(2026, 8, 11, 0, 0))
    warsaw_like = timezone(timedelta(hours=2))
    with pytest.raises(ValueError, match="must use UTC"):
        target_local_date_at(datetime(2026, 8, 11, 0, 0, tzinfo=warsaw_like))
