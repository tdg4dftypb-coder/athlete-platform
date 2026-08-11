from dataclasses import replace
from datetime import date, datetime, timezone
import json

import duckdb
import pytest

from morning_briefing.input_models import (
    BiomarkerBriefingInput,
    BiomarkerBriefingSignalInput,
    MorningBriefingInput,
    RecoveryBriefingInput,
    TrainingBriefingInput,
)
from production_runtime.assessment_snapshot import (
    AssessmentSnapshot,
    AssessmentSnapshotCodec,
    AssessmentSnapshotConflictError,
    AssessmentSnapshotIntegrityError,
)
from production_runtime.persistence import DuckDbAssessmentSnapshotRepository


NOW = datetime(2026, 8, 11, 4, tzinfo=timezone.utc)
TARGET = date(2026, 8, 11)


def input_value(load=320.5):
    return MorningBriefingInput(
        generated_at=NOW,
        recovery=RecoveryBriefingInput(82, "READY", "good", False, "normal", "normal", "good"),
        training=TrainingBriefingInput(
            "Tempo", "60 minutes", 60, "MODERATE", True, "TEMPO", load, "LOW"
        ),
        biomarkers=BiomarkerBriefingInput(
            3, 1, "one marker", False, 0,
            (BiomarkerBriefingSignalInput("FERRITIN", "LOW", "VERIFIED", None),),
            "available",
        ),
    )


def snapshot(runtime_id="runtime-1", value=None):
    value = value or input_value()
    return AssessmentSnapshot(
        runtime_id, TARGET, NOW, value, AssessmentSnapshotCodec.artifact_id_for(value)
    )


def test_canonical_round_trip_and_deterministic_digest():
    codec = AssessmentSnapshotCodec()
    first = snapshot()
    assert codec.decode(codec.encode(first)) == first
    assert codec.encode(first) == codec.encode(first)
    assert AssessmentSnapshotCodec.artifact_id_for(input_value()) == first.artifact_id
    assert AssessmentSnapshotCodec.artifact_id_for(input_value(321.0)) != first.artifact_id
    assert json.loads(codec.encode(first))["input"]["biomarkers"]["signals"][0]["canonical_code"] == "FERRITIN"


def test_repository_idempotency_conflict_and_lookup(tmp_path):
    repo = DuckDbAssessmentSnapshotRepository(tmp_path / "runtime.duckdb")
    first = snapshot()
    repo.save(first)
    repo.save(first)
    assert repo.get_by_runtime_id("runtime-1") == first
    assert repo.get_by_artifact_id(first.artifact_id) == first
    with pytest.raises(AssessmentSnapshotConflictError):
        repo.save(snapshot(value=input_value(999.0)))
    assert repo.get_by_runtime_id("missing") is None


@pytest.mark.parametrize(
    "column,value",
    [
        ("snapshot_schema_version", "9.0"),
        ("runtime_id", "different-runtime"),
        ("target_local_date", date(2026, 8, 12)),
        ("artifact_id", "assessment:sha256:" + "0" * 64),
    ],
)
def test_repository_detects_index_and_payload_integrity_mismatch(tmp_path, column, value):
    path = tmp_path / "runtime.duckdb"
    repo = DuckDbAssessmentSnapshotRepository(path)
    repo.save(snapshot())
    connection = duckdb.connect(str(path))
    connection.execute(
        f"UPDATE production_runtime_assessment_snapshots SET {column} = ?",
        [value],
    )
    connection.close()
    with pytest.raises(AssessmentSnapshotIntegrityError):
        repo.get_by_runtime_id("different-runtime" if column == "runtime_id" else "runtime-1")


def test_codec_rejects_invalid_schema_and_malformed_payload():
    codec = AssessmentSnapshotCodec()
    payload = json.loads(codec.encode(snapshot()))
    payload["schema_version"] = "9.0"
    with pytest.raises(AssessmentSnapshotIntegrityError):
        codec.decode(json.dumps(payload))
    with pytest.raises(AssessmentSnapshotIntegrityError):
        codec.decode("not-json")
