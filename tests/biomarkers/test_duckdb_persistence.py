"""
Comprehensive Unit and Integration Test Suite for DuckDB Persistence Adapter (Sprint 7A).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
import duckdb

from biomarkers.composition import BiomarkersApplicationContext, build_repository_from_env
from biomarkers.deletion import DeletionMode
from biomarkers.errors import ImportRunActivationError, ReportNotFoundError
from biomarkers.ingestion import RawLaboratoryRow
from biomarkers.models import (
    BiomarkerValueType,
    ImportRunStatus,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReferenceRange,
    LaboratoryReport,
    NormalizationStatus,
    PlatformMessageLevel,
    VerificationStatus,
)
from biomarkers.persistence.duckdb_repository import DuckDBLaboratoryRepository
from biomarkers.persistence.migrations import SCHEMA_VERSION, run_migrations


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test_biomarkers.duckdb")


@pytest.fixture
def duckdb_repo(temp_db_path: str) -> DuckDBLaboratoryRepository:
    return DuckDBLaboratoryRepository(db_path=temp_db_path)


def test_schema_and_migrations_idempotency(temp_db_path: str) -> None:
    conn = duckdb.connect(temp_db_path)
    v1 = run_migrations(conn)
    assert v1 == SCHEMA_VERSION

    # Re-run migration should be idempotent
    v2 = run_migrations(conn)
    assert v2 == SCHEMA_VERSION

    tables = [
        row[0]
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
    ]
    assert "schema_version" in tables
    assert "laboratory_reports" in tables
    assert "laboratory_import_runs" in tables
    assert "laboratory_observations" in tables
    assert "laboratory_tombstones" in tables

    # Ensure privacy: no filename or document_content columns
    cols = [
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='laboratory_reports'"
        ).fetchall()
    ]
    assert "filename" not in cols
    assert "original_filename" not in cols
    assert "content_bytes" not in cols
    conn.close()


def test_laboratory_report_round_trip(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    now = datetime.now(timezone.utc)
    report = LaboratoryReport(
        report_id="rep-101",
        collected_at=now,
        reported_at=now,
        laboratory_name="Synevo Warszawa",
        source_type="pdf_digital",
        source_document_hash="hash-abc-123",
        created_at=now,
    )
    import_run = LaboratoryImportRun(
        import_run_id="run-101",
        report_id="rep-101",
        parser_version="1.0",
        extractor_version="1.0",
        registry_version="1.0",
        unit_rules_version="1.0",
        started_at=now,
        completed_at=now,
        status=ImportRunStatus.COMPLETED,
        active=True,
        warnings=("Warning line 1",),
        observations=(),
    )

    duckdb_repo.save_report_with_import_run(report, import_run)

    loaded_rep = duckdb_repo.get_report("rep-101")
    assert loaded_rep is not None
    assert loaded_rep.report_id == "rep-101"
    assert loaded_rep.laboratory_name == "Synevo Warszawa"
    assert loaded_rep.source_document_hash == "hash-abc-123"
    assert loaded_rep.collected_at.tzinfo == timezone.utc

    found_rep = duckdb_repo.find_report_by_source_hash("hash-abc-123")
    assert found_rep is not None
    assert found_rep.report_id == "rep-101"


def test_laboratory_observation_full_round_trip(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    now = datetime.now(timezone.utc)
    report = LaboratoryReport(
        report_id="rep-202",
        collected_at=now,
        reported_at=None,
        laboratory_name="Diagnostyka S.A.",
        source_type="csv",
        source_document_hash="hash-obs-999",
        created_at=now,
    )

    obs = LaboratoryObservation(
        observation_id="obs-001",
        import_run_id="run-202",
        report_id="rep-202",
        report_row_index=1,
        observation_source_fingerprint="fp-ferritin-001",
        raw_name="Ferrytyna",
        raw_value="145.5",
        raw_unit="µg/L",
        canonical_code="ferritin",
        normalization_status=NormalizationStatus.RESOLVED,
        requires_review=False,
        alias_match_confidence=1.0,
        value_type=BiomarkerValueType.NUMERIC,
        numeric_value=145.5,
        text_value=None,
        qualitative_value=None,
        inequality_operator=None,
        range_low=30.0,
        range_high=200.0,
        normalized_value=145.5,
        normalized_unit="µg/L",
        laboratory_reference_range=LaboratoryReferenceRange(low=30.0, high=200.0, text="30 - 200", unit="µg/L"),
        laboratory_flag="N",
        laboratory_provided_critical_flag=None,
        collected_at=now,
        reported_at=now,
        laboratory_name="Diagnostyka S.A.",
        source_type="csv",
        source_document_hash="hash-obs-999",
        name_confidence=1.0,
        value_confidence=1.0,
        unit_confidence=1.0,
        reference_confidence=1.0,
        extraction_confidence=1.0,
        overall_confidence=1.0,
        verification_status=VerificationStatus.VERIFIED,
        trend_status=None,
        training_context_signal=None,
        platform_message_level=PlatformMessageLevel.INFORMATIONAL,
        is_possible_duplicate=False,
        metadata={"extraction_method": "regex"},
    )

    import_run = LaboratoryImportRun(
        import_run_id="run-202",
        report_id="rep-202",
        parser_version="1.0",
        extractor_version="1.0",
        registry_version="1.0",
        unit_rules_version="1.0",
        started_at=now,
        completed_at=now,
        status=ImportRunStatus.COMPLETED,
        active=True,
        warnings=(),
        observations=(obs,),
    )

    duckdb_repo.save_report_with_import_run(report, import_run)

    active_run = duckdb_repo.get_active_import_run("rep-202")
    assert active_run is not None
    assert active_run.import_run_id == "run-202"
    assert len(active_run.observations) == 1

    loaded_obs = active_run.observations[0]
    assert loaded_obs.observation_id == "obs-001"
    assert loaded_obs.raw_name == "Ferrytyna"
    assert loaded_obs.canonical_code == "ferritin"
    assert loaded_obs.normalized_value == 145.5
    assert loaded_obs.laboratory_reference_range is not None
    assert loaded_obs.laboratory_reference_range.low == 30.0
    assert loaded_obs.laboratory_reference_range.high == 200.0
    assert loaded_obs.overall_confidence == 1.0
    assert loaded_obs.metadata == {"extraction_method": "regex"}
    assert loaded_obs.collected_at.tzinfo == timezone.utc


def test_atomic_activation_invariant(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    now = datetime.now(timezone.utc)
    report = LaboratoryReport(
        report_id="rep-atomic",
        collected_at=now,
        reported_at=None,
        laboratory_name="Lab A",
        source_type="csv",
        source_document_hash="hash-atomic-001",
        created_at=now,
    )

    run_1 = LaboratoryImportRun(
        import_run_id="run-1",
        report_id="rep-atomic",
        parser_version="1.0",
        extractor_version="1.0",
        registry_version="1.0",
        unit_rules_version="1.0",
        started_at=now,
        completed_at=now,
        status=ImportRunStatus.COMPLETED,
        active=True,
        warnings=(),
        observations=(),
    )
    run_2 = LaboratoryImportRun(
        import_run_id="run-2",
        report_id="rep-atomic",
        parser_version="2.0",
        extractor_version="2.0",
        registry_version="1.0",
        unit_rules_version="1.0",
        started_at=now,
        completed_at=now,
        status=ImportRunStatus.COMPLETED,
        active=False,
        warnings=(),
        observations=(),
    )

    duckdb_repo.save_report_with_import_run(report, run_1)
    duckdb_repo.save_report_with_import_run(report, run_2)

    # Activate run_2
    duckdb_repo.activate_import_run("rep-atomic", "run-2")

    active = duckdb_repo.get_active_import_run("rep-atomic")
    assert active is not None
    assert active.import_run_id == "run-2"

    runs = duckdb_repo.get_import_runs("rep-atomic")
    assert len(runs) == 2
    active_count = sum(1 for r in runs if r.active)
    assert active_count == 1

    with pytest.raises(ReportNotFoundError):
        duckdb_repo.activate_import_run("non-existent-rep", "run-2")

    with pytest.raises(ImportRunActivationError):
        duckdb_repo.activate_import_run("rep-atomic", "non-existent-run")


def test_find_observations_for_duplicate_check(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    now = datetime.now(timezone.utc)
    rep_a = LaboratoryReport(
        report_id="rep-a",
        collected_at=now,
        reported_at=None,
        laboratory_name="Lab A",
        source_type="csv",
        source_document_hash="hash-dup-a",
        created_at=now,
    )
    rep_b = LaboratoryReport(
        report_id="rep-b",
        collected_at=now,
        reported_at=None,
        laboratory_name="Lab B",
        source_type="csv",
        source_document_hash="hash-dup-b",
        created_at=now,
    )

    obs_a = LaboratoryObservation(
        observation_id="obs-a",
        import_run_id="run-a",
        report_id="rep-a",
        report_row_index=1,
        observation_source_fingerprint="fp-a",
        raw_name="Ferrytyna",
        raw_value="100",
        raw_unit="µg/L",
        canonical_code="ferritin",
        normalization_status=NormalizationStatus.RESOLVED,
        requires_review=False,
        alias_match_confidence=1.0,
        value_type=BiomarkerValueType.NUMERIC,
        numeric_value=100.0,
        text_value=None,
        qualitative_value=None,
        inequality_operator=None,
        range_low=30.0,
        range_high=200.0,
        normalized_value=100.0,
        normalized_unit="µg/L",
        laboratory_reference_range=None,
        laboratory_flag=None,
        laboratory_provided_critical_flag=None,
        collected_at=now,
        reported_at=now,
        laboratory_name="Lab A",
        source_type="csv",
        source_document_hash="hash-dup-a",
        name_confidence=1.0,
        value_confidence=1.0,
        unit_confidence=1.0,
        reference_confidence=1.0,
        extraction_confidence=1.0,
        overall_confidence=1.0,
        verification_status=VerificationStatus.VERIFIED,
        trend_status=None,
        training_context_signal=None,
        platform_message_level=PlatformMessageLevel.INFORMATIONAL,
        is_possible_duplicate=False,
        metadata={},
    )

    duckdb_repo.save_report_with_import_run(rep_a, LaboratoryImportRun(
        import_run_id="run-a", report_id="rep-a", parser_version="1.0", extractor_version="1.0",
        registry_version="1.0", unit_rules_version="1.0", started_at=now, completed_at=now,
        status=ImportRunStatus.COMPLETED, active=True, warnings=(), observations=(obs_a,)
    ))

    matches = duckdb_repo.find_observations_for_duplicate_check(
        canonical_code="ferritin",
        collected_at=now,
        normalized_value=100.0,
        exclude_report_id="rep-b",
    )
    assert len(matches) == 1
    assert matches[0].observation_id == "obs-a"

    no_matches = duckdb_repo.find_observations_for_duplicate_check(
        canonical_code="ferritin",
        collected_at=now,
        normalized_value=100.0,
        exclude_report_id="rep-a",
    )
    assert len(no_matches) == 0


def test_deletion_modes_and_tombstones(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    now = datetime.now(timezone.utc)
    report = LaboratoryReport(
        report_id="rep-del-1",
        collected_at=now,
        reported_at=None,
        laboratory_name="Lab Delete",
        source_type="csv",
        source_document_hash="hash-del-123",
        created_at=now,
    )
    import_run = LaboratoryImportRun(
        import_run_id="run-del-1",
        report_id="rep-del-1",
        parser_version="1.0",
        extractor_version="1.0",
        registry_version="1.0",
        unit_rules_version="1.0",
        started_at=now,
        completed_at=now,
        status=ImportRunStatus.COMPLETED,
        active=True,
        warnings=(),
        observations=(),
    )

    duckdb_repo.save_report_with_import_run(report, import_run)

    # 1. DELETE_DATA_KEEP_TOMBSTONE
    res_tomb = duckdb_repo.delete_report("rep-del-1", DeletionMode.DELETE_DATA_KEEP_TOMBSTONE)
    assert res_tomb.deleted_reports_count == 1
    assert res_tomb.tombstone_retained is True

    assert duckdb_repo.get_report("rep-del-1") is None
    assert duckdb_repo.find_report_by_source_hash("hash-del-123") is None

    # 2. Re-insert report with new ID & DELETE_EVERYTHING
    rep_2 = LaboratoryReport(
        report_id="rep-del-2",
        collected_at=now,
        reported_at=None,
        laboratory_name="Lab Delete 2",
        source_type="csv",
        source_document_hash="hash-del-456",
        created_at=now,
    )
    duckdb_repo.save_report_with_import_run(rep_2, LaboratoryImportRun(
        import_run_id="run-del-2", report_id="rep-del-2", parser_version="1.0", extractor_version="1.0",
        registry_version="1.0", unit_rules_version="1.0", started_at=now, completed_at=now,
        status=ImportRunStatus.COMPLETED, active=True, warnings=(), observations=()
    ))

    res_all = duckdb_repo.delete_report("rep-del-2", DeletionMode.DELETE_EVERYTHING)
    assert res_all.deleted_reports_count == 1
    assert res_all.tombstone_retained is False


def test_process_restart_lifecycle_integration(tmp_path: Path) -> None:
    """
    CRITICAL TEST (Section 11):
    1. Create temporary DB file.
    2. Context A ingests synthetic laboratory result.
    3. Close Context A connection.
    4. Context B connects to same DB file.
    5. Verify report, active run, observations exist, and dashboard payload builds correctly.
    6. Confirm private fields do not leak into serialization payload.
    """
    db_file = str(tmp_path / "restart_lifecycle.duckdb")

    # Phase 1: Context A ingests data
    ctx_a = BiomarkersApplicationContext(db_path=db_file, repository=DuckDBLaboratoryRepository(db_path=db_file))

    from biomarkers.ingestion import LaboratoryIngestionRequest

    req = LaboratoryIngestionRequest(
        content=b"1 | Ferrytyna | 85.0 | ug/L | 30-200\n2 | Zelazko | 110.0 | ug/dL | 65-175",
        laboratory_name_fallback="Synevo Poznań",
        source_type="pdf_digital",
    )

    ingest_res = ctx_a.ingestion_service.ingest(req)
    assert ingest_res.report is not None
    report_id = ingest_res.report.report_id

    ctx_a.repository._conn.close()

    # Phase 2: Context B opens exact same DB file
    repo_b = DuckDBLaboratoryRepository(db_path=db_file)
    ctx_b = BiomarkersApplicationContext(repository=repo_b)

    loaded_report = ctx_b.repository.get_report(report_id)
    assert loaded_report is not None
    assert loaded_report.laboratory_name == "Synevo Poznań"

    active_run = ctx_b.repository.get_active_import_run(report_id)
    assert active_run is not None
    assert len(active_run.observations) == 2

    payload = ctx_b.get_dashboard_payload()
    assert payload["contract_version"] == "1.0"
    assert payload["metadata"]["status"] in ("ready", "partial")
    assert payload["summary"]["total_reports"] == 1
    assert payload["summary"]["total_observations"] == 2

    payload_str = json.dumps(payload)
    assert "hash-restart-999" not in payload_str
    assert "filename" not in payload_str

    for unres in payload["unresolved_items"]:
        assert "raw_value" not in unres

    repo_b._conn.close()


def test_composition_repository_factory_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = str(tmp_path / "env_test.duckdb")
    monkeypatch.setenv("BIOMARKERS_REPOSITORY", "duckdb")
    monkeypatch.setenv("BIOMARKERS_DB_PATH", db_file)

    repo = build_repository_from_env()
    assert isinstance(repo, DuckDBLaboratoryRepository)
    repo._conn.close()

    monkeypatch.setenv("BIOMARKERS_REPOSITORY", "in_memory")
    repo_mem = build_repository_from_env()
    assert not isinstance(repo_mem, DuckDBLaboratoryRepository)
