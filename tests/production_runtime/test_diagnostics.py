from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import duckdb
import pytest

from production_runtime import (
    RUNTIME_CONTRACT_VERSION,
    PhaseStatus,
    ProductionDailyRuntimeResult,
    RuntimeFailure,
    RuntimeOperationalHealth,
    RuntimeOperationalStatusReader,
    RuntimePhase,
    RuntimePhaseResult,
    RuntimeResumability,
    RuntimeStatus,
    RuntimeWarning,
    SourceWatermark,
    logical_execution_key,
)
from production_runtime.diagnostics_composition import create_runtime_operational_status_reader
from production_runtime.persistence import DuckDbRuntimeAuditRepository
from production_runtime.repository import RuntimeAuditRepositoryError


TARGET = date(2026, 8, 11)
START = datetime(2026, 8, 11, 5, 0, tzinfo=timezone.utc)


class FixedClock:
    def __init__(self, instant):
        self.instant = instant

    def now_utc(self):
        return self.instant


def attempt(runtime_id="runtime-1", started_at=START):
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


def ingestion_phase(started_at=START):
    return RuntimePhaseResult(
        RuntimePhase.INGESTION,
        PhaseStatus.COMPLETED,
        started_at,
        started_at + timedelta(minutes=2),
        True,
        2,
        ("a.fit", "b.fit"),
        (),
    )


def running_revision_two(initial=None):
    initial = initial or attempt()
    return replace(
        initial,
        revision=2,
        phases=(ingestion_phase(initial.started_at_utc),),
        activities_discovered=2,
    )


def partial_result(initial=None, *, degraded=False):
    current = running_revision_two(initial)
    fact_phase = RuntimePhaseResult(
        RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION,
        PhaseStatus.FAILED if degraded else PhaseStatus.COMPLETED,
        current.started_at_utc + timedelta(minutes=2),
        current.started_at_utc + timedelta(minutes=3),
        not degraded,
        2,
        ("event-1", "event-2"),
        ("phase_interrupted",) if degraded else (),
    )
    return replace(
        current,
        revision=3,
        status=RuntimeStatus.PARTIAL,
        completed_at_utc=current.started_at_utc + timedelta(minutes=4),
        phases=current.phases + (fact_phase,),
        activity_facts_created=1,
        activities_already_present=1,
        source_watermarks=(
            SourceWatermark("fit_directory", "directory_snapshot_sha256", "sha256:abc", START),
        ),
        warnings=(RuntimeWarning("phase_interrupted", "bounded detail", "b.fit"),) if degraded else (),
        failure=(
            RuntimeFailure("phase_interrupted", RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION)
            if degraded else None
        ),
    )


def persist(repo, *records):
    for index, record in enumerate(records):
        repo.append(record, expected_revision=None if index == 0 else records[index - 1].revision)


def reader(repo, now=START + timedelta(minutes=10), stale_after=timedelta(minutes=30)):
    return RuntimeOperationalStatusReader(repo, FixedClock(now), stale_after)


@pytest.mark.parametrize("phase_count", (4, 5, 6, 7, 8))
def test_later_canonical_running_prefixes_are_same_attempt_resumable(phase_count, tmp_path):
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    initial = attempt()
    phases = tuple(
        RuntimePhaseResult(
            phase,
            PhaseStatus.SKIPPED if phase is RuntimePhase.RECONCILIATION else PhaseStatus.COMPLETED,
            START,
            START,
            False,
            artifact_ids=("assessment:sha256:abc",) if phase is RuntimePhase.ASSESSMENT else (),
        )
        for phase in tuple(RuntimePhase)[:phase_count]
    )
    record = replace(initial, phases=phases)
    repo.append(record)
    assert reader(repo).get_latest().resumability is RuntimeResumability.RESUME_SAME_ATTEMPT


def test_no_audit_data_returns_none_and_empty_history(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    status = reader(repo)
    assert status.get_latest() is None
    assert status.get_latest_for_date(TARGET) is None
    assert status.list_for_date(TARGET) == ()


def test_latest_global_attempt_uses_repository_ordering(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    older = attempt("runtime-old", START)
    newer = attempt("runtime-new", START + timedelta(hours=1))
    repo.append(older)
    repo.append(newer)
    assert reader(repo, now=START + timedelta(hours=1, minutes=1)).get_latest().runtime_id == "runtime-new"


def test_latest_and_all_attempts_for_date_remain_visible(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    first = attempt("runtime-a", START)
    second = attempt("runtime-b", START + timedelta(minutes=5))
    repo.append(first)
    repo.append(second)
    status = reader(repo)
    assert status.get_latest_for_date(TARGET).runtime_id == "runtime-b"
    snapshots = status.list_for_date(TARGET)
    assert tuple(item.runtime_id for item in snapshots) == ("runtime-a", "runtime-b")
    assert snapshots[0].logical_execution_key == snapshots[1].logical_execution_key


def test_explicit_runtime_id_and_unknown_id(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    repo.append(attempt("runtime-exact"))
    status = reader(repo)
    assert status.get_by_runtime_id("runtime-exact").revision == 1
    assert status.get_by_runtime_id("missing") is None


@pytest.mark.parametrize(
    ("record_factory", "expected"),
    [
        (attempt, RuntimeResumability.RESUME_SAME_ATTEMPT),
        (running_revision_two, RuntimeResumability.RESUME_SAME_ATTEMPT),
        (partial_result, RuntimeResumability.START_NEW_ATTEMPT),
    ],
)
def test_current_ingestion_slice_resumability(record_factory, expected, tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    record = record_factory()
    if record.revision == 1:
        repo.append(record)
    elif record.revision == 2:
        persist(repo, attempt(), record)
    else:
        persist(repo, attempt(), running_revision_two(), record)
    assert reader(repo).get_latest().resumability is expected


def test_failed_and_completed_are_terminal_diagnostics(tmp_path) -> None:
    failed_repo = DuckDbRuntimeAuditRepository(tmp_path / "failed.duckdb")
    initial = attempt()
    failed = replace(
        initial,
        revision=2,
        status=RuntimeStatus.FAILED,
        completed_at_utc=START + timedelta(minutes=1),
        failure=RuntimeFailure("persistence_unavailable", RuntimePhase.INGESTION),
    )
    persist(failed_repo, initial, failed)
    failed_snapshot = reader(failed_repo).get_latest()
    assert failed_snapshot.health is RuntimeOperationalHealth.FAILED
    assert failed_snapshot.resumability is RuntimeResumability.START_NEW_ATTEMPT

    completed_repo = DuckDbRuntimeAuditRepository(tmp_path / "completed.duckdb")
    complete_initial = attempt("runtime-completed")
    completed = replace(
        complete_initial,
        revision=2,
        status=RuntimeStatus.COMPLETED,
        completed_at_utc=START + timedelta(minutes=1),
    )
    persist(completed_repo, complete_initial, completed)
    completed_snapshot = reader(completed_repo).get_latest()
    assert completed_snapshot.health is RuntimeOperationalHealth.HEALTHY
    assert completed_snapshot.resumability is RuntimeResumability.NO_ACTION
    assert completed_snapshot.next_expected_phase is None


def test_successful_partial_is_healthy_but_failed_partial_is_degraded(tmp_path) -> None:
    healthy_repo = DuckDbRuntimeAuditRepository(tmp_path / "healthy.duckdb")
    persist(healthy_repo, attempt(), running_revision_two(), partial_result())
    assert reader(healthy_repo).get_latest().health is RuntimeOperationalHealth.HEALTHY

    degraded_repo = DuckDbRuntimeAuditRepository(tmp_path / "degraded.duckdb")
    persist(degraded_repo, attempt(), running_revision_two(), partial_result(degraded=True))
    snapshot = reader(degraded_repo).get_latest()
    assert snapshot.health is RuntimeOperationalHealth.DEGRADED
    assert snapshot.failure.code == "phase_interrupted"
    assert snapshot.failure.phase is RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION
    assert snapshot.warnings[0].code == "phase_interrupted"


def test_stale_running_uses_last_durable_progress_and_injected_clock(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    persist(repo, attempt(), running_revision_two())
    snapshot = reader(
        repo,
        now=START + timedelta(minutes=40),
        stale_after=timedelta(minutes=30),
    ).get_latest()
    assert snapshot.last_durable_progress_at_utc == START + timedelta(minutes=2)
    assert snapshot.stale_running is True
    assert snapshot.health is RuntimeOperationalHealth.STALE


def test_recent_running_is_not_stale(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    repo.append(attempt())
    snapshot = reader(repo, now=START + timedelta(minutes=29)).get_latest()
    assert snapshot.stale_running is False
    assert snapshot.health is RuntimeOperationalHealth.HEALTHY


def test_diagnostics_rejects_non_utc_injected_clock(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    repo.append(attempt())
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        RuntimeOperationalStatusReader(
            repo,
            FixedClock(datetime(2026, 8, 11, 5, 0)),
        ).get_latest()


def test_phase_diagnostics_are_canonical_and_missing_is_not_fabricated(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    persist(repo, attempt(), running_revision_two())
    phases = reader(repo).get_latest().phases
    assert tuple(item.phase for item in phases) == tuple(RuntimePhase)
    assert phases[0].present is True
    assert phases[0].status is PhaseStatus.COMPLETED
    assert phases[0].artifact_ids == ("a.fit", "b.fit")
    assert all(item.present is False and item.status is None for item in phases[1:])


def test_next_expected_phase_is_defensible_for_current_revisions(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    repo.append(attempt())
    assert reader(repo).get_latest().next_expected_phase is RuntimePhase.INGESTION
    persist_repo = DuckDbRuntimeAuditRepository(tmp_path / "audit-two.duckdb")
    persist(persist_repo, attempt(), running_revision_two())
    assert reader(persist_repo).get_latest().next_expected_phase is RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION


def test_watermarks_counters_and_references_are_projected_exactly(tmp_path) -> None:
    repo = DuckDbRuntimeAuditRepository(tmp_path / "audit.duckdb")
    final = partial_result()
    persist(repo, attempt(), running_revision_two(), final)
    snapshot = reader(repo).get_latest()
    assert snapshot.source_watermarks == final.source_watermarks
    assert snapshot.counters.activities_discovered == 2
    assert snapshot.counters.activity_facts_created == 1
    assert snapshot.counters.activities_already_present == 1
    assert snapshot.counters.reconciliations_created is None
    assert snapshot.artifact_references.decision_id is None
    assert snapshot.artifact_references.morning_briefing_available is False


def test_read_only_repository_refuses_append_and_missing_file_is_unavailable(tmp_path) -> None:
    db_path = tmp_path / "audit.duckdb"
    writer = DuckDbRuntimeAuditRepository(db_path)
    writer.append(attempt())
    read_only = DuckDbRuntimeAuditRepository(db_path, read_only=True)
    with pytest.raises(RuntimeAuditRepositoryError, match="read-only"):
        read_only.append(attempt("other"))
    with pytest.raises(RuntimeAuditRepositoryError, match="unavailable"):
        DuckDbRuntimeAuditRepository(tmp_path / "missing.duckdb", read_only=True)


def test_read_only_composition_opens_only_existing_audit_database(tmp_path) -> None:
    db_path = tmp_path / "audit.duckdb"
    writer = DuckDbRuntimeAuditRepository(db_path)
    writer.append(attempt())
    status = create_runtime_operational_status_reader(
        db_path,
        clock=FixedClock(START + timedelta(minutes=1)),
    )
    assert status.get_latest().runtime_id == "runtime-1"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["audit.duckdb"]
