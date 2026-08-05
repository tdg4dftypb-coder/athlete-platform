"""
Integration Test Suite for ImportLaboratoryPdfUseCase and CLI Utility (Sprint 7B).
"""

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import pytest

from biomarkers.composition import BiomarkersApplicationContext
from biomarkers.deletion import DeletionMode
from biomarkers.models import ImportRunStatus
from biomarkers.persistence.duckdb_repository import DuckDBLaboratoryRepository
from biomarkers.use_cases import ImportLaboratoryPdfUseCase, PdfImportSummary
from tests.biomarkers.test_pdf_extractor import create_synthetic_pdf


@pytest.fixture
def synthetic_pdf_bytes() -> bytes:
    lines = [
        "Laboratorium Synevo Warszawa",
        "Data pobrania: 05.08.2026 08:30",
        "Glukoza | 92.5 | mg/dL | 70 - 99 |",
        "Ferrytyna | 14,2 | µg/L | 30.0 - 200.0 | L",
        "TSH | < 0.01 | mIU/L | 0.27 - 4.20 |",
        "Nierozpoznany Marker | 55 | U/mL | 0 - 100 | H",
        "Strona 1 z 1",
    ]
    return create_synthetic_pdf(lines)


def test_dry_run_import_does_not_modify_database(tmp_path: Path, synthetic_pdf_bytes: bytes) -> None:
    db_file = str(tmp_path / "dry_run.duckdb")
    ctx = BiomarkersApplicationContext(db_path=db_file)

    use_case = ImportLaboratoryPdfUseCase(ingestion_service=ctx.ingestion_service)
    summary = use_case.execute(synthetic_pdf_bytes, dry_run=True)

    assert isinstance(summary, PdfImportSummary)
    assert summary.dry_run is True
    assert summary.status == ImportRunStatus.COMPLETED
    assert summary.extracted_rows_count == 4
    assert summary.imported_observations_count == 4
    assert summary.unresolved_observations_count == 1  # "Nierozpoznany Marker"

    # Confirm zero reports were stored in persistent DuckDB repository
    all_reports = ctx.repository.get_all_reports()
    assert len(all_reports) == 0


def test_persistent_pdf_import_and_read_model_integration(tmp_path: Path, synthetic_pdf_bytes: bytes) -> None:
    db_file = str(tmp_path / "persistent_pdf.duckdb")

    # Phase 1: Context A imports PDF
    ctx_a = BiomarkersApplicationContext(db_path=db_file, repository=DuckDBLaboratoryRepository(db_path=db_file))
    use_case_a = ImportLaboratoryPdfUseCase(ingestion_service=ctx_a.ingestion_service)

    summary_a = use_case_a.execute(synthetic_pdf_bytes, dry_run=False)
    assert summary_a.dry_run is False
    assert summary_a.report_id is not None
    assert summary_a.imported_observations_count == 4

    ctx_a.repository.close()

    # Phase 2: Context B connects to same DB file and builds dashboard payload
    repo_b = DuckDBLaboratoryRepository(db_path=db_file)
    ctx_b = BiomarkersApplicationContext(repository=repo_b)

    payload = ctx_b.get_dashboard_payload()
    assert payload["contract_version"] == "1.0"
    assert payload["summary"]["total_reports"] == 1
    assert payload["metadata"]["status"] in ("ready", "partial")

    # Confirm private fields do not leak in payload
    payload_str = str(payload)
    assert "source_document_hash" not in payload_str
    assert "filename" not in payload_str

    repo_b.close()


def test_idempotent_reimport_of_same_pdf(tmp_path: Path, synthetic_pdf_bytes: bytes) -> None:
    db_file = str(tmp_path / "idempotent_pdf.duckdb")
    ctx = BiomarkersApplicationContext(db_path=db_file, repository=DuckDBLaboratoryRepository(db_path=db_file))
    use_case = ImportLaboratoryPdfUseCase(ingestion_service=ctx.ingestion_service)

    summary_1 = use_case.execute(synthetic_pdf_bytes, dry_run=False)
    assert summary_1.duplicate_document is False

    # Second import of exact same content bytes
    summary_2 = use_case.execute(synthetic_pdf_bytes, dry_run=False)
    assert summary_2.duplicate_document is True
    assert "SHA-256 duplicate" in summary_2.warnings[0]

    all_reports = ctx.repository.get_all_reports()
    assert len(all_reports) == 1
    ctx.repository.close()


def test_tombstoned_pdf_reimport_blocked(tmp_path: Path, synthetic_pdf_bytes: bytes) -> None:
    db_file = str(tmp_path / "tombstoned_pdf.duckdb")
    ctx = BiomarkersApplicationContext(db_path=db_file, repository=DuckDBLaboratoryRepository(db_path=db_file))
    use_case = ImportLaboratoryPdfUseCase(ingestion_service=ctx.ingestion_service)

    summary = use_case.execute(synthetic_pdf_bytes, dry_run=False)
    report_id = summary.report_id

    # Delete with tombstone retention
    ctx.repository.delete_report(report_id, DeletionMode.DELETE_DATA_KEEP_TOMBSTONE)

    # Attempt re-import
    re_summary = use_case.execute(synthetic_pdf_bytes, dry_run=False)
    assert re_summary.status == ImportRunStatus.FAILED
    assert re_summary.duplicate_document is True
    assert "tombstone" in re_summary.warnings[0].lower()

    all_reports = ctx.repository.get_all_reports()
    assert len(all_reports) == 0
    ctx.repository.close()


def test_cli_import_pdf_script_execution(tmp_path: Path, synthetic_pdf_bytes: bytes) -> None:
    pdf_path = str(tmp_path / "test_report.pdf")
    db_path = str(tmp_path / "cli_test.duckdb")
    Path(pdf_path).write_bytes(synthetic_pdf_bytes)

    # 1. Test CLI dry-run
    cmd_dry = [
        sys.executable,
        "scripts/import_laboratory_pdf.py",
        pdf_path,
        "--db-path", db_path,
        "--dry-run",
        "--show-summary",
    ]
    res_dry = subprocess.run(cmd_dry, capture_output=True, text=True)
    assert res_dry.returncode == 0
    assert "[DRY-RUN]" in res_dry.stdout
    assert "Extracted Rows:" in res_dry.stdout

    # Confirm zero health raw values leak in output
    assert "92.5" not in res_dry.stdout
    assert "14,2" not in res_dry.stdout

    # 2. Test CLI persistent import
    cmd_imp = [
        sys.executable,
        "scripts/import_laboratory_pdf.py",
        pdf_path,
        "--db-path", db_path,
        "--show-summary",
    ]
    res_imp = subprocess.run(cmd_imp, capture_output=True, text=True)
    assert res_imp.returncode == 0
    assert "completed successfully" in res_imp.stdout
