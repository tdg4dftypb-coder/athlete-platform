from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os

import duckdb
import pytest

from application.standard_fit_ingestion import (
    StandardActivityFactSynchronizationService, StandardFitWorkoutIngestionService,
)
from athlete.memory.activity_recorded import ActivityRecordedWriter
from athlete.memory.models import AthleteMemoryEventType
from athlete.memory.repository import AthleteMemoryRepository
from core.database import Database
from integrations.zwift_fit.discovery import ZwiftFitArtifactDiscovery, ZwiftSourceUnavailable
from integrations.zwift_fit.identity import ZwiftFitSourceIdentity
from integrations.zwift_fit.models import SourceTrust
from integrations.zwift_fit.persistence import ZwiftFitRepository, ZwiftFitSchema
from integrations.zwift_fit.service import ZwiftFitSyncService
from production_runtime.paths import get_zwift_activity_source_path
from repositories.workout_repository import WorkoutRepository
from schema.athlete_memory_schema import AthleteMemorySchema
from schema.training_schema import TrainingSchema
from training.ingestion.parsed_activity import ParsedActivity, ParsedActivityRecord

NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)


class Parser:
    def parse(self, path):
        if "bad" in open(path, "rb").read().decode(errors="ignore"):
            raise ValueError("corrupt")
        start = datetime(2026, 8, 17, 8)
        return ParsedActivity(
            start, start + timedelta(hours=1), "cycling", 30000, 500,
            [ParsedActivityRecord(start, 180, 140, 85, 8.0),
             ParsedActivityRecord(start + timedelta(hours=1), 220, 150, 90, 9.0)],
        )


def write(path, data=b"valid", age=120):
    path.write_bytes(data)
    timestamp = NOW.timestamp() - age
    os.utime(path, (timestamp, timestamp))
    return path


def test_configuration_is_explicit_and_has_no_core_default(tmp_path, monkeypatch):
    monkeypatch.delenv("ZWIFT_ACTIVITY_SOURCE_PATH", raising=False)
    assert get_zwift_activity_source_path() is None
    assert get_zwift_activity_source_path(tmp_path) == tmp_path


def test_discovery_filters_and_orders_stable_fit_files(tmp_path):
    write(tmp_path / "b.fit")
    write(tmp_path / "a.FIT", b"a", age=180)
    write(tmp_path / "note.txt")
    write(tmp_path / ".temporary.fit")
    (tmp_path / "empty.fit").write_bytes(b"")
    (tmp_path / "directory.fit").mkdir()
    unstable = write(tmp_path / "new.fit", age=10)
    snapshot = ZwiftFitArtifactDiscovery(tmp_path).discover(NOW)
    assert [path.name for path in snapshot.ready] == ["a.FIT", "b.fit"]
    assert snapshot.unstable == (unstable,)
    assert {path.name for path in snapshot.discovered} == {"a.FIT", "b.fit", "new.fit"}


def test_missing_folder_is_typed_unavailable(tmp_path):
    with pytest.raises(ZwiftSourceUnavailable):
        ZwiftFitArtifactDiscovery(tmp_path / "missing").discover(NOW)


def test_bootstrap_and_scan_are_bounded_and_late_copy_is_visible(tmp_path):
    old = write(tmp_path / "old.fit", age=91 * 86400)
    for index in range(510):
        write(tmp_path / f"{index:03}.fit", str(index).encode(), age=120 + index)
    late = write(tmp_path / "late-copy.fit", old.read_bytes(), age=120)
    snapshot = ZwiftFitArtifactDiscovery(tmp_path).discover(NOW)
    assert old not in snapshot.discovered and late in snapshot.discovered
    assert len(snapshot.discovered) == 500


def test_identity_is_hash_not_filename_and_provider_is_explicit(tmp_path):
    first = write(tmp_path / "first.fit", b"same")
    renamed = write(tmp_path / "renamed.fit", b"same")
    changed = write(tmp_path / "changed.fit", b"different")
    factory = ZwiftFitSourceIdentity()
    assert factory.create(first) == factory.create(renamed)
    assert factory.create(first) != factory.create(changed)
    assert factory.create(first).provider == "zwift_fit"
    assert factory.create(first).external_id == f"sha256:{sha256(b'same').hexdigest()}"


@pytest.fixture
def context(tmp_path):
    folder = tmp_path / "Zwift Activities"
    folder.mkdir()
    database = Database(tmp_path / "health.duckdb")
    TrainingSchema(database).create()
    AthleteMemorySchema(database).create()
    ZwiftFitSchema.create(database.connection)
    workouts = WorkoutRepository(database)
    memory = AthleteMemoryRepository(database)
    ingestion = StandardFitWorkoutIngestionService(workouts, parser=Parser())
    synchronization = StandardActivityFactSynchronizationService(
        workouts, ActivityRecordedWriter(memory),
    )
    service = ZwiftFitSyncService(
        ZwiftFitArtifactDiscovery(folder), ingestion, synchronization,
        ZwiftFitRepository(database.connection),
    )
    yield folder, database, workouts, memory, service
    database.close()


def test_new_fit_ingests_workout_fact_candidate_and_provenance(context):
    folder, database, workouts, memory, service = context
    artifact = write(folder / "ride.fit")
    result = service.sync(started_at=NOW)
    identity = ZwiftFitSourceIdentity().create(artifact)
    event = memory.get_by_source_identity(
        AthleteMemoryEventType.ACTIVITY_RECORDED, "zwift_fit", identity.external_id,
    )
    assert (result.discovered, result.ready, result.ingested) == (1, 1, 1)
    assert workouts.count() == 1 and event is not None
    candidate = result.candidates[0]
    assert candidate.provider == "zwift_fit" and candidate.external_id == identity.external_id
    assert candidate.start_at.tzinfo == timezone.utc and candidate.end_at.tzinfo == timezone.utc
    assert candidate.duration_seconds == 3600 and candidate.sport == "cycling"
    assert candidate.distance_meters == 30000 and candidate.trust is SourceTrust.HIGH_FIDELITY
    assert candidate.artifact_reference == "ride.fit" and "/" not in candidate.artifact_reference
    assert candidate.fingerprint.startswith("sha256:")
    assert database.connection.execute("SELECT COUNT(*) FROM zwift_fit_sync_audit").fetchone() == (1,)


def test_repeat_rename_and_copy_are_noop_by_content(context):
    folder, _, workouts, memory, service = context
    write(folder / "ride.fit", b"same")
    first = service.sync(started_at=NOW)
    write(folder / "renamed.fit", b"same")
    second = service.sync(started_at=NOW + timedelta(minutes=5))
    assert first.ingested == 1 and second.ingested == 0 and second.duplicate == 2
    assert workouts.count() == 1
    assert len(memory.load_between(datetime(2026, 8, 17), datetime(2026, 8, 18))) == 1


def test_same_filename_changed_bytes_is_new_identity(context):
    folder, _, workouts, _, service = context
    path = write(folder / "ride.fit", b"first")
    service.sync(started_at=NOW)
    write(path, b"second")
    result = service.sync(started_at=NOW + timedelta(minutes=5))
    assert result.ingested == 1 and workouts.count() == 2


def test_malformed_is_isolated_and_valid_after_it_ingests(context):
    folder, _, workouts, _, service = context
    write(folder / "a.fit", b"bad")
    write(folder / "b.fit", b"valid")
    result = service.sync(started_at=NOW)
    assert (result.malformed, result.ingested, result.failed) == (1, 1, 0)
    assert result.failures[0].code == "malformed_fit" and workouts.count() == 1


def test_unstable_is_reported_not_ingested(context):
    folder, _, workouts, _, service = context
    write(folder / "writing.fit", age=10)
    result = service.sync(started_at=NOW)
    assert result.skipped_not_stable == 1 and result.ready == 0 and workouts.count() == 0


def test_generic_standard_path_keeps_fit_file_provider(context):
    folder, _, workouts, memory, _ = context
    artifact = write(folder / "generic.fit", b"generic")
    StandardFitWorkoutIngestionService(workouts, parser=Parser()).ingest(artifact)
    result = StandardActivityFactSynchronizationService(
        workouts, ActivityRecordedWriter(memory)
    ).synchronize(artifact)
    assert result.source_type == "fit_file"
