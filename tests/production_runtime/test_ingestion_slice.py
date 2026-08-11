from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pytest

from application.standard_fit_ingestion import (
    StandardActivityFactSynchronizationService,
    StandardFitWorkoutIngestionService,
)
from athlete.memory.activity_recorded import ActivityRecordedWriter
from athlete.memory.models import AthleteMemoryEventType
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from production_runtime import (
    FitArtifactDiscovery,
    IngestionRuntimeSlice,
    RuntimeAttemptNotResumableError,
    RuntimePhase,
    RuntimeStatus,
)
from production_runtime.ingestion_composition import (
    create_production_ingestion_runtime_slice,
)
from production_runtime.ingestion_slice import (
    INVALID_ACTIVITY_ARTIFACT,
    PERSISTENCE_UNAVAILABLE,
    SOURCE_UNAVAILABLE,
)
from production_runtime.paths import (
    get_default_fit_activity_source_path,
    get_default_health_db_path,
)
from production_runtime.persistence import DuckDbRuntimeAuditRepository
from repositories.workout_repository import WorkoutRepository
from schema.athlete_memory_schema import AthleteMemorySchema
from schema.training_schema import TrainingSchema
from training.ingestion.fit_file_source_identity import FitFileSourceIdentity
from training.ingestion.parsed_activity import ParsedActivity, ParsedActivityRecord


TARGET = date(2026, 8, 11)
CLOCK_START = datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc)


class IncrementingClock:
    def __init__(self, start=CLOCK_START):
        self.current = start

    def now_utc(self):
        value = self.current
        self.current += timedelta(seconds=1)
        return value


class FixtureParser:
    def parse(self, path: str):
        if Path(path).name.startswith("malformed"):
            raise ValueError("invalid FIT fixture")
        start = datetime(2026, 8, 11, 6, 0)
        return ParsedActivity(
            start=start,
            end=start + timedelta(minutes=1),
            sport="cycling",
            distance=500.0,
            calories=20,
            records=[
                ParsedActivityRecord(start, 180, 130, 85, 8.0),
                ParsedActivityRecord(start + timedelta(minutes=1), 200, 140, 90, 9.0),
            ],
        )


def build_slice(tmp_path, *, ingestion=None, synchronization=None, clock=None, runtime_ids=None):
    fit_dir = tmp_path / "fits"
    fit_dir.mkdir(exist_ok=True)
    database = Database(tmp_path / "health.duckdb")
    TrainingSchema(database).create()
    AthleteMemorySchema(database).create()
    workouts = WorkoutRepository(database)
    memory = AthleteMemoryRepository(database)
    audit = DuckDbRuntimeAuditRepository(tmp_path / "runtime.duckdb")
    ids = iter(runtime_ids or ("runtime-1", "runtime-2", "runtime-3"))
    runtime_slice = IngestionRuntimeSlice(
        audit_repository=audit,
        discovery=FitArtifactDiscovery(fit_dir),
        ingestion=ingestion or StandardFitWorkoutIngestionService(workouts, parser=FixtureParser()),
        fact_synchronization=synchronization or StandardActivityFactSynchronizationService(
            workouts, ActivityRecordedWriter(memory)
        ),
        clock=clock or IncrementingClock(),
        runtime_id_factory=lambda: next(ids),
    )
    return runtime_slice, database, workouts, memory, audit, fit_dir


def test_successful_empty_source_is_partial_whole_runtime(tmp_path) -> None:
    runtime_slice, database, _, _, _, _ = build_slice(tmp_path)
    result = runtime_slice.run_new_attempt(TARGET)
    assert result.status is RuntimeStatus.PARTIAL
    assert result.activities_discovered == 0
    assert result.activity_facts_created == 0
    assert result.activities_already_present == 0
    assert tuple(item.phase for item in result.phases) == (
        RuntimePhase.INGESTION,
        RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION,
    )
    assert all(item.status.value == "completed" for item in result.phases)
    database.close()


def test_new_fit_persists_workout_and_canonical_fact(tmp_path) -> None:
    runtime_slice, database, workouts, memory, _, fit_dir = build_slice(tmp_path)
    fit_path = fit_dir / "ride.fit"
    fit_path.write_bytes(b"valid-fit")
    result = runtime_slice.run_new_attempt(TARGET)
    identity = FitFileSourceIdentity().create(fit_path)
    event = memory.get_by_source_identity(
        AthleteMemoryEventType.ACTIVITY_RECORDED,
        identity.provider,
        identity.external_id,
    )
    assert workouts.count() == 1
    assert event is not None
    assert event.event_type is AthleteMemoryEventType.ACTIVITY_RECORDED
    assert result.activities_discovered == 1
    assert result.activity_facts_created == 1
    assert result.activities_already_present == 0
    database.close()


def test_second_attempt_is_domain_idempotent(tmp_path) -> None:
    runtime_slice, database, workouts, memory, audit, fit_dir = build_slice(tmp_path)
    fit_path = fit_dir / "ride.fit"
    fit_path.write_bytes(b"unchanged")
    first = runtime_slice.run_new_attempt(TARGET)
    second = runtime_slice.run_new_attempt(TARGET)
    identity = FitFileSourceIdentity().create(fit_path)
    events = memory.load_between(datetime(2026, 8, 11), datetime(2026, 8, 12))
    assert first.runtime_id != second.runtime_id
    assert first.logical_execution_key == second.logical_execution_key
    assert workouts.count() == 1
    assert len(events) == 1
    assert events[0].source_key == identity.external_id
    assert second.activity_facts_created == 0
    assert second.activities_already_present == 1
    assert len(audit.list_for_target_date(TARGET)) == 2
    database.close()


def test_existing_workout_missing_fact_is_repaired(tmp_path) -> None:
    runtime_slice, database, workouts, memory, _, fit_dir = build_slice(tmp_path)
    fit_path = fit_dir / "repair.fit"
    fit_path.write_bytes(b"repair")
    StandardFitWorkoutIngestionService(workouts, parser=FixtureParser()).ingest(fit_path)
    result = runtime_slice.run_new_attempt(TARGET)
    identity = FitFileSourceIdentity().create(fit_path)
    assert workouts.count() == 1
    assert memory.get_by_source_identity(
        AthleteMemoryEventType.ACTIVITY_RECORDED,
        identity.provider,
        identity.external_id,
    ) is not None
    assert result.phases[0].changed_state is False
    assert result.phases[1].changed_state is True
    assert result.activity_facts_created == 1
    database.close()


def test_malformed_fit_does_not_block_valid_artifact(tmp_path) -> None:
    runtime_slice, database, workouts, _, _, fit_dir = build_slice(tmp_path)
    (fit_dir / "malformed.fit").write_bytes(b"bad")
    (fit_dir / "valid.fit").write_bytes(b"good")
    result = runtime_slice.run_new_attempt(TARGET)
    assert result.status is RuntimeStatus.PARTIAL
    assert result.failure.code == INVALID_ACTIVITY_ARTIFACT
    assert result.failure.phase is RuntimePhase.INGESTION
    assert result.activities_discovered == 2
    assert workouts.count() == 1
    assert result.activity_facts_created == 1
    assert result.phases[0].status.value == "failed"
    database.close()


class FailingIngestion:
    def ingest(self, path):
        raise duckdb.IOException("database is locked")


class FailingSynchronization:
    def synchronize(self, path):
        raise duckdb.IOException("database is locked")


def test_ingestion_persistence_failure_is_failed_attempt(tmp_path) -> None:
    runtime_slice, database, _, _, audit, fit_dir = build_slice(
        tmp_path, ingestion=FailingIngestion()
    )
    (fit_dir / "ride.fit").write_bytes(b"ride")
    result = runtime_slice.run_new_attempt(TARGET)
    assert result.status is RuntimeStatus.FAILED
    assert result.failure.code == PERSISTENCE_UNAVAILABLE
    assert result.failure.phase is RuntimePhase.INGESTION
    assert audit.get_by_runtime_id(result.runtime_id) == result
    database.close()


def test_fact_sync_persistence_failure_preserves_ingestion_phase(tmp_path) -> None:
    runtime_slice, database, _, _, _, fit_dir = build_slice(
        tmp_path, synchronization=FailingSynchronization()
    )
    (fit_dir / "ride.fit").write_bytes(b"ride")
    result = runtime_slice.run_new_attempt(TARGET)
    assert result.status is RuntimeStatus.PARTIAL
    assert result.failure.code == PERSISTENCE_UNAVAILABLE
    assert tuple(item.phase for item in result.phases) == (
        RuntimePhase.INGESTION,
        RuntimePhase.ACTIVITY_FACT_SYNCHRONIZATION,
    )
    assert result.phases[0].status.value == "completed"
    database.close()


def test_audit_revision_progression_is_running_running_partial(tmp_path) -> None:
    runtime_slice, database, _, _, _, _ = build_slice(tmp_path)
    result = runtime_slice.run_new_attempt(TARGET)
    connection = duckdb.connect(str(tmp_path / "runtime.duckdb"))
    try:
        rows = connection.execute(
            """SELECT revision, status FROM production_runtime_audit_revisions
               WHERE runtime_id = ? ORDER BY revision""",
            [result.runtime_id],
        ).fetchall()
    finally:
        connection.close()
    assert rows == [(1, "running"), (2, "running"), (3, "partial")]
    database.close()


class InterruptingSlice(IngestionRuntimeSlice):
    def _execute_fact_synchronization(self, artifacts):
        raise KeyboardInterrupt


def test_resume_same_attempt_after_ingestion_audit(tmp_path) -> None:
    normal, database, workouts, memory, audit, fit_dir = build_slice(tmp_path)
    (fit_dir / "ride.fit").write_bytes(b"ride")
    interrupted = InterruptingSlice(
        audit,
        normal._discovery,
        normal._ingestion,
        normal._fact_synchronization,
        clock=normal._clock,
        runtime_id_factory=lambda: "runtime-1",
    )
    with pytest.raises(KeyboardInterrupt):
        interrupted.run_new_attempt(TARGET)
    checkpoint = audit.get_by_runtime_id("runtime-1")
    assert checkpoint.revision == 2
    assert checkpoint.status is RuntimeStatus.RUNNING
    resumed = normal.resume_attempt("runtime-1")
    assert resumed.revision == 3
    assert resumed.status is RuntimeStatus.PARTIAL
    assert workouts.count() == 1
    assert len(memory.load_between(datetime(2026, 8, 11), datetime(2026, 8, 12))) == 1
    database.close()


def test_partial_attempt_requires_new_attempt_not_resume(tmp_path) -> None:
    runtime_slice, database, _, _, _, _ = build_slice(tmp_path)
    result = runtime_slice.run_new_attempt(TARGET)
    with pytest.raises(RuntimeAttemptNotResumableError):
        runtime_slice.resume_attempt(result.runtime_id)
    database.close()


def test_target_date_is_independent_from_clock_date_and_timestamps_are_utc(tmp_path) -> None:
    runtime_slice, database, _, _, _, _ = build_slice(tmp_path)
    target = date(2025, 1, 2)
    result = runtime_slice.run_new_attempt(target)
    assert result.target_local_date == target
    assert result.started_at_utc.date() == CLOCK_START.date()
    assert result.started_at_utc.utcoffset() == timedelta(0)
    assert result.completed_at_utc.utcoffset() == timedelta(0)
    database.close()


def test_source_watermarks_are_real_snapshot_hashes(tmp_path) -> None:
    runtime_slice, database, _, _, _, fit_dir = build_slice(tmp_path)
    (fit_dir / "ride.fit").write_bytes(b"ride")
    result = runtime_slice.run_new_attempt(TARGET)
    assert tuple(item.kind for item in result.source_watermarks) == (
        "directory_snapshot_sha256",
        "fit_source_identity_set_sha256",
    )
    assert all(item.value.startswith("sha256:") for item in result.source_watermarks)
    database.close()


def test_missing_source_is_bounded_failed_attempt(tmp_path) -> None:
    runtime_slice, database, _, _, _, fit_dir = build_slice(tmp_path)
    fit_dir.rmdir()
    result = runtime_slice.run_new_attempt(TARGET)
    assert result.status is RuntimeStatus.FAILED
    assert result.failure.code == SOURCE_UNAVAILABLE
    database.close()


def test_no_later_domain_side_effect_references_are_populated(tmp_path) -> None:
    runtime_slice, database, _, _, _, _ = build_slice(tmp_path)
    result = runtime_slice.run_new_attempt(TARGET)
    assert result.decision_id is None
    assert result.training_plan_id is None
    assert result.prescription_id is None
    assert result.reconciliations_created is None
    assert result.morning_briefing_available is False
    database.close()


def test_paths_are_injectable_and_repo_anchored(tmp_path, monkeypatch) -> None:
    health = tmp_path / "health.duckdb"
    source = tmp_path / "source"
    assert get_default_health_db_path(health) == health
    assert get_default_fit_activity_source_path(source) == source
    monkeypatch.setenv("HEALTH_DB_PATH", "tmp/health.duckdb")
    assert get_default_health_db_path().is_absolute()


def test_owned_database_closes_on_success(tmp_path) -> None:
    fit_dir = tmp_path / "fits"
    fit_dir.mkdir()
    container = create_production_ingestion_runtime_slice(
        health_db_path=tmp_path / "health.duckdb",
        runtime_audit_db_path=tmp_path / "runtime.duckdb",
        fit_source_path=fit_dir,
        clock=IncrementingClock(),
        runtime_id_factory=lambda: "runtime-owned",
    )
    with container:
        container.runtime_slice.run_new_attempt(TARGET)
    with pytest.raises(duckdb.ConnectionException):
        container.database.connection.execute("SELECT 1")


def test_owned_database_closes_on_failure(tmp_path) -> None:
    missing = tmp_path / "missing"
    container = create_production_ingestion_runtime_slice(
        health_db_path=tmp_path / "health.duckdb",
        runtime_audit_db_path=tmp_path / "runtime.duckdb",
        fit_source_path=missing,
        clock=IncrementingClock(),
        runtime_id_factory=lambda: "runtime-owned-failure",
    )
    with container:
        result = container.runtime_slice.run_new_attempt(TARGET)
        assert result.status is RuntimeStatus.FAILED
    with pytest.raises(duckdb.ConnectionException):
        container.database.connection.execute("SELECT 1")
