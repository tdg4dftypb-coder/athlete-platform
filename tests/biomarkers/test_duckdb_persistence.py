"""
Comprehensive Unit and Integration Test Suite for DuckDB Persistence Adapter (Sprint 7A & 7A.1).
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pytest
import duckdb

from biomarkers.composition import BiomarkersApplicationContext, build_repository_from_env
from biomarkers.deletion import DeletionMode
from biomarkers.errors import ImportRunActivationError, ReportNotFoundError
from biomarkers.ingestion import LaboratoryIngestionRequest, RawLaboratoryRow
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

    conn.close()


def test_schema_future_version_protection(temp_db_path: str) -> None:
    conn = duckdb.connect(temp_db_path)
    run_migrations(conn)
    conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (999, CURRENT_TIMESTAMP)")

    with pytest.raises(ValueError, match="newer than supported version"):
        run_migrations(conn)
    conn.close()


def test_tombstone_reingestion_prevention(temp_db_path: str) -> None:
    """
    TOMBSTONE AUDIT TEST (Section 1):
    1. Ingest document.
    2. DELETE_DATA_KEEP_TOMBSTONE.
    3. Attempt automatic re-ingestion of exact same document bytes.
    4. Assert: Re-ingestion blocked, status FAILED, warning issued, 0 new reports/obs created.
    """
    ctx = BiomarkersApplicationContext(db_path=temp_db_path, repository=DuckDBLaboratoryRepository(db_path=temp_db_path))

    req = LaboratoryIngestionRequest(
        content=b"1 | Ferrytyna | 85.0 | ug/L | 30-200",
        laboratory_name_fallback="Synevo Warszawa",
        source_type="pdf_digital",
    )

    ingest_res = ctx.ingestion_service.ingest(req)
    assert ingest_res.report is not None
    report_id = ingest_res.report.report_id
    doc_hash = ingest_res.report.source_document_hash

    # Delete with tombstone retention
    del_res = ctx.repository.delete_report(report_id, DeletionMode.DELETE_DATA_KEEP_TOMBSTONE)
    assert del_res.tombstone_retained is True
    assert ctx.repository.is_source_tombstoned(doc_hash) is True

    # Re-ingest exact same content bytes
    re_ingest_res = ctx.ingestion_service.ingest(req)
    assert re_ingest_res.report is None
    assert re_ingest_res.import_run is None
    assert len(re_ingest_res.observations) == 0
    assert re_ingest_res.status == ImportRunStatus.FAILED
    assert re_ingest_res.duplicate_document is True
    assert "tombstone" in re_ingest_res.warnings[0].lower()

    # Confirm database has 0 reports, 0 observations, and retained tombstone
    all_reports = ctx.repository.get_all_reports()
    assert len(all_reports) == 0


def test_datetime_round_trip_aware_utc(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    """DATETIME ROUND-TRIP TEST (Section 2)."""
    now = datetime.now(timezone.utc)

    report = LaboratoryReport(
        report_id="rep-tz",
        collected_at=now,
        reported_at=now,
        laboratory_name="Lab TZ",
        source_type="csv",
        source_document_hash="hash-tz-123",
        created_at=now,
    )
    import_run = LaboratoryImportRun(
        import_run_id="run-tz",
        report_id="rep-tz",
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

    loaded = duckdb_repo.get_report("rep-tz")
    assert loaded is not None

    for dt_attr in [loaded.collected_at, loaded.reported_at, loaded.created_at]:
        assert dt_attr is not None
        assert dt_attr.tzinfo == timezone.utc
        assert dt_attr.utcoffset() == timedelta(0)
        assert dt_attr.isoformat().endswith("+00:00") or dt_attr.isoformat().endswith("Z")


def test_transaction_rollback_on_activation_failure(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    """TRANSACTION ROLLBACK TEST (Section 3)."""
    now = datetime.now(timezone.utc)
    report = LaboratoryReport(
        report_id="rep-roll",
        collected_at=now,
        reported_at=None,
        laboratory_name="Lab Rollback",
        source_type="csv",
        source_document_hash="hash-roll-001",
        created_at=now,
    )

    run_1 = LaboratoryImportRun(
        import_run_id="run-1-active",
        report_id="rep-roll",
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
    duckdb_repo.save_report_with_import_run(report, run_1)

    # Attempt activation of invalid run ID -> should raise ImportRunActivationError and rollback
    with pytest.raises(ImportRunActivationError):
        duckdb_repo.activate_import_run("rep-roll", "invalid-run-id")

    # Verify previous active run remains active (no orphaned state with 0 active runs)
    active = duckdb_repo.get_active_import_run("rep-roll")
    assert active is not None
    assert active.import_run_id == "run-1-active"
    assert active.active is True


def test_comprehensive_value_types_round_trip(duckdb_repo: DuckDBLaboratoryRepository) -> None:
    """ROUND-TRIP COVERAGE TEST FOR ALL VALUE TYPES (Section 4)."""
    now = datetime.now(timezone.utc)
    report = LaboratoryReport(
        report_id="rep-types",
        collected_at=now,
        reported_at=None,
        laboratory_name="Lab Types",
        source_type="csv",
        source_document_hash="hash-types-001",
        created_at=now,
    )

    obs_numeric = LaboratoryObservation(
        observation_id="obs-num",
        import_run_id="run-types",
        report_id="rep-types",
        report_row_index=1,
        observation_source_fingerprint="fp-num",
        raw_name="Ferrytyna",
        raw_value="14.2",
        raw_unit="µg/L",
        canonical_code="ferritin",
        normalization_status=NormalizationStatus.RESOLVED,
        requires_review=False,
        alias_match_confidence=1.0,
        value_type=BiomarkerValueType.NUMERIC,
        numeric_value=14.2,
        normalized_value=14.2,
        normalized_unit="µg/L",
        laboratory_reference_range=LaboratoryReferenceRange(low=10.0, high=50.0, text="10-50", unit="µg/L"),
        laboratory_flag="L",
        laboratory_provided_critical_flag="CRITICAL",
        collected_at=now,
        verification_status=VerificationStatus.VERIFIED,
        platform_message_level=PlatformMessageLevel.ATTENTION,
        metadata={"key": "val"},
    )

    obs_inequality = LaboratoryObservation(
        observation_id="obs-ineq",
        import_run_id="run-types",
        report_id="rep-types",
        report_row_index=2,
        observation_source_fingerprint="fp-ineq",
        raw_name="CRP",
        raw_value="< 0.1",
        raw_unit="mg/L",
        canonical_code="crp",
        normalization_status=NormalizationStatus.RESOLVED,
        requires_review=False,
        value_type=BiomarkerValueType.BOUNDED_INEQUALITY,
        numeric_value=0.1,
        inequality_operator="<",
        normalized_value=0.1,
        normalized_unit="mg/L",
        collected_at=now,
        verification_status=VerificationStatus.VERIFIED,
    )

    obs_text = LaboratoryObservation(
        observation_id="obs-txt",
        import_run_id="run-types",
        report_id="rep-types",
        report_row_index=3,
        observation_source_fingerprint="fp-txt",
        raw_name="Mocz Wygląd",
        raw_value="Przejrzysty",
        raw_unit="",
        canonical_code=None,
        normalization_status=NormalizationStatus.UNRESOLVED,
        requires_review=True,
        value_type=BiomarkerValueType.TEXT,
        text_value="Przejrzysty",
        collected_at=now,
        verification_status=VerificationStatus.UNVERIFIED,
    )

    import_run = LaboratoryImportRun(
        import_run_id="run-types",
        report_id="rep-types",
        parser_version="1.0",
        extractor_version="1.0",
        registry_version="1.0",
        unit_rules_version="1.0",
        started_at=now,
        completed_at=now,
        status=ImportRunStatus.COMPLETED,
        active=True,
        warnings=("Warning 1",),
        observations=(obs_numeric, obs_inequality, obs_text),
    )

    duckdb_repo.save_report_with_import_run(report, import_run)

    active_run = duckdb_repo.get_active_import_run("rep-types")
    assert active_run is not None
    assert len(active_run.observations) == 3

    obs_map = {o.observation_id: o for o in active_run.observations}

    num = obs_map["obs-num"]
    assert num.numeric_value == 14.2
    assert num.laboratory_flag == "L"
    assert num.laboratory_provided_critical_flag == "CRITICAL"
    assert num.laboratory_reference_range.low == 10.0
    assert num.laboratory_reference_range.high == 50.0

    ineq = obs_map["obs-ineq"]
    assert ineq.inequality_operator == "<"
    assert ineq.numeric_value == 0.1

    txt = obs_map["obs-txt"]
    assert txt.canonical_code is None
    assert txt.normalization_status == NormalizationStatus.UNRESOLVED
    assert txt.text_value == "Przejrzysty"


def test_repository_lifecycle_close(temp_db_path: str) -> None:
    """REPOSITORY LIFECYCLE TEST (Section 6)."""
    repo = DuckDBLaboratoryRepository(db_path=temp_db_path)
    now = datetime.now(timezone.utc)
    report = LaboratoryReport(
        report_id="rep-close",
        collected_at=now,
        source_type="csv",
        source_document_hash="hash-close-123",
        created_at=now,
    )
    run = LaboratoryImportRun(
        import_run_id="run-close",
        report_id="rep-close",
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
    repo.save_report_with_import_run(report, run)

    # Close connection
    repo.close()
    # Idempotent close
    repo.close()

    # Operations after close should raise controlled RuntimeError
    with pytest.raises(RuntimeError, match="closed"):
        repo.get_report("rep-close")

    # Re-open repo on same file
    repo_2 = DuckDBLaboratoryRepository(db_path=temp_db_path)
    assert repo_2.get_report("rep-close") is not None
    repo_2.close()


def test_privacy_audit_no_forbidden_fields(temp_db_path: str) -> None:
    """PRIVACY AUDIT TEST (Section 7)."""
    conn = duckdb.connect(temp_db_path)
    run_migrations(conn)

    for table in ["laboratory_reports", "laboratory_import_runs", "laboratory_observations", "laboratory_tombstones"]:
        cols = [
            row[0]
            for row in conn.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"
            ).fetchall()
        ]
        assert "filename" not in cols
        assert "original_filename" not in cols
        assert "content_bytes" not in cols
        assert "stack_trace" not in cols
        assert "medical_diagnosis" not in cols

    conn.close()
