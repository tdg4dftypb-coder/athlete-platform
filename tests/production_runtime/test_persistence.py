from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import duckdb
import pytest

from production_runtime import (
    RUNTIME_CONTRACT_VERSION,
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimeAuditConflictError,
    RuntimeAuditDataError,
    RuntimeFailure,
    RuntimePhase,
    RuntimePhaseResult,
    RuntimeStatus,
    RuntimeWarning,
    SourceWatermark,
    logical_execution_key,
)
from production_runtime.composition import create_runtime_audit_repository
from production_runtime.persistence import (
    DuckDbRuntimeAuditRepository,
    RuntimeAuditCodec,
    get_default_runtime_audit_db_path,
)


TARGET = date(2026, 8, 11)
START = datetime(2026, 8, 11, 4, 0, tzinfo=timezone.utc)


def runtime_attempt(runtime_id: str = "runtime-a", started_at: datetime = START):
    return ProductionDailyRuntimeResult(
        runtime_id=runtime_id,
        logical_execution_key=logical_execution_key(TARGET),
        revision=1,
        contract_version=RUNTIME_CONTRACT_VERSION,
        target_local_date=TARGET,
        timezone_name="Europe/Warsaw",
        started_at_utc=started_at,
        completed_at_utc=None,
        status=RuntimeStatus.RUNNING,
    )


def terminal_result(initial, status=RuntimeStatus.COMPLETED):
    phase = RuntimePhaseResult(
        phase=RuntimePhase.INGESTION,
        status=PhaseStatus.COMPLETED,
        started_at_utc=initial.started_at_utc,
        completed_at_utc=initial.started_at_utc + timedelta(seconds=3),
        changed_state=True,
        item_count=1,
        artifact_ids=("activity-1",),
        warning_codes=("STALE_INPUT",),
    )
    failure = RuntimeFailure("OPTIONAL_PHASE_FAILED", RuntimePhase.PUBLICATION) if status is RuntimeStatus.FAILED else None
    return replace(
        initial,
        revision=2,
        status=status,
        completed_at_utc=initial.started_at_utc + timedelta(seconds=5),
        phases=(phase,),
        decision_id="decision-1",
        training_plan_id="plan-1",
        prescription_id="rx-1",
        morning_briefing_available=status is RuntimeStatus.COMPLETED,
        activities_discovered=2,
        activity_facts_created=1,
        activities_already_present=1,
        reconciliations_created=1,
        source_watermarks=(SourceWatermark("health", "max_date", "2026-08-10", START),),
        warnings=(RuntimeWarning("STALE_INPUT", source="health"),),
        failure=failure,
    )


def test_fresh_schema_and_exact_round_trip(tmp_path) -> None:
    db_path = tmp_path / "runtime.duckdb"
    repo = DuckDbRuntimeAuditRepository(db_path)
    initial = runtime_attempt()
    repo.append(initial)
    assert repo.get_by_runtime_id(initial.runtime_id) == initial
    connection = duckdb.connect(str(db_path))
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM production_runtime_audit_revisions"
        ).fetchone()[0] == 1
    finally:
        connection.close()


@pytest.mark.parametrize("status", [RuntimeStatus.COMPLETED, RuntimeStatus.PARTIAL, RuntimeStatus.FAILED])
def test_lifecycle_revision_round_trip_with_optional_contract_fields(tmp_path, status) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / f"{status.value}.duckdb")
    initial = runtime_attempt()
    final = terminal_result(initial, status)
    repo.append(initial)
    repo.append(final, expected_revision=1)
    assert repo.get_by_runtime_id(initial.runtime_id) == final


def test_multiple_attempts_for_same_target_date_are_preserved(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "attempts.duckdb")
    first = runtime_attempt("runtime-a", START)
    second = runtime_attempt("runtime-b", START + timedelta(minutes=5))
    repo.append(second)
    repo.append(first)
    assert repo.list_for_target_date(TARGET) == (first, second)


def test_latest_attempt_ordering_is_deterministic(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "latest.duckdb")
    repo.append(runtime_attempt("runtime-a", START))
    latest = runtime_attempt("runtime-z", START + timedelta(minutes=1))
    repo.append(latest)
    assert repo.get_latest() == latest


def test_duplicate_identical_revision_is_idempotent(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "idempotent.duckdb")
    initial = runtime_attempt()
    repo.append(initial)
    repo.append(initial)
    assert repo.list_for_target_date(TARGET) == (initial,)


def test_same_revision_different_payload_conflicts_without_overwrite(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "conflict.duckdb")
    initial = runtime_attempt()
    repo.append(initial)
    conflicting = replace(initial, warnings=(RuntimeWarning("STALE_INPUT"),))
    with pytest.raises(RuntimeAuditConflictError, match="different payload"):
        repo.append(conflicting)
    assert repo.get_by_runtime_id(initial.runtime_id) == initial


def test_transition_requires_expected_revision_and_next_revision(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "cas.duckdb")
    initial = runtime_attempt()
    repo.append(initial)
    with pytest.raises(RuntimeAuditConflictError, match="latest is 1"):
        repo.append(terminal_result(initial), expected_revision=2)


def test_terminal_attempt_cannot_transition(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "terminal.duckdb")
    initial = runtime_attempt()
    final = terminal_result(initial)
    repo.append(initial)
    repo.append(final, expected_revision=1)
    with pytest.raises(RuntimeAuditConflictError, match="Terminal"):
        repo.append(replace(final, revision=3), expected_revision=2)


def test_persisted_phase_results_cannot_be_rewritten(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "phases.duckdb")
    initial = runtime_attempt()
    checkpoint = replace(initial, revision=2, phases=(terminal_result(initial).phases[0],))
    repo.append(initial)
    repo.append(checkpoint, expected_revision=1)
    changed_phase = replace(checkpoint.phases[0], item_count=99)
    with pytest.raises(RuntimeAuditConflictError, match="phase results"):
        repo.append(replace(checkpoint, revision=3, phases=(changed_phase,)), expected_revision=2)


def test_codec_rejects_unknown_schema_version() -> None:
    codec = RuntimeAuditCodec()
    payload = codec.encode(runtime_attempt()).replace('"schema_version":"1.0"', '"schema_version":"9.0"')
    with pytest.raises(RuntimeAuditDataError, match="unsupported schema_version"):
        codec.decode(payload)


def test_timezone_aware_timestamps_reconstruct_after_file_reopen(tmp_path) -> None:
    db_path = tmp_path / "reopen.duckdb"
    first = DuckDbRuntimeAuditRepository(db_path)
    final = terminal_result(runtime_attempt())
    first.append(runtime_attempt())
    first.append(final, expected_revision=1)
    reopened = DuckDbRuntimeAuditRepository(db_path)
    loaded = reopened.get_by_runtime_id("runtime-a")
    assert loaded == final
    assert loaded.started_at_utc.tzinfo is not None
    assert loaded.completed_at_utc.utcoffset() == timedelta(0)


def test_path_resolution_and_minimal_composition(tmp_path, monkeypatch) -> None:
    explicit = tmp_path / "explicit.duckdb"
    assert get_default_runtime_audit_db_path(explicit) == explicit
    environment = tmp_path / "environment.duckdb"
    monkeypatch.setenv("RUNTIME_AUDIT_DB_PATH", str(environment))
    assert get_default_runtime_audit_db_path() == environment
    repo = create_runtime_audit_repository(explicit)
    repo.append(runtime_attempt())
    assert repo.get_latest().runtime_id == "runtime-a"
