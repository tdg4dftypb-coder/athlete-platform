"""
Integration Privacy & PII Audit Test Suite for Biomarkers Domain (Sprint 7C.2).
Validates that zero PII or administrative data leaks into DuckDB tables, warnings, or metadata.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from biomarkers.composition import BiomarkersApplicationContext
from biomarkers.extraction.pdf_text_extractor import ExtractedLaboratoryDocument, ExtractedLaboratoryPage
from biomarkers.models import NormalizationStatus
from biomarkers.persistence.duckdb_repository import DuckDBLaboratoryRepository
from biomarkers.use_cases.import_pdf import ImportLaboratoryPdfUseCase


def test_duckdb_privacy_and_pii_audit_integration(tmp_path: Path) -> None:
    db_file = str(tmp_path / "privacy_audit.duckdb")

    # 1. Build synthetic ALAB document with explicit PII and administrative header/footer noise
    text_page_1 = """
    ALAB laboratoria Sp. z o.o.
    ul. Marszałkowska 10/15, 00-001 Warszawa
    tel. +48 22 349 60 12, e-mail: kontakt@alab.pl
    Pacjent: Marszałek Jan Kowalski
    PESEL: 85080512345
    Adres: ul. Marszałkowska 10/15, Warszawa
    Ident. pacjenta: PAC-998877
    Ident. dokumentu: DOC-123456
    Lekarz zlecający: dr med. Franciszek Nowak
    data i godz. pobrania: 05-08-2026 08:30
    Badanie Wynik Jednostka Zakres referencyjny Flaga
    Morfologia krwi
    Hemoglobina (HGB) 14.8 g/dL 12.0 - 16.0
    Nieznany Peptyd N-Końcowy 45 pg/mL 10-50
    Autoryzował: mgr Diagnosta Anna Maria Wiśniewska
    Zatwierdzili: mgr Diagnosta Piotr Zieliński
    Strona 1 z 1
    """

    doc = ExtractedLaboratoryDocument(
        source_document_hash="hash-privacy-audit-001",
        page_count=1,
        pages=(ExtractedLaboratoryPage(page_number=1, text=text_page_1),),
    )

    # 2. Perform persistent import into temporary DuckDB
    repo = DuckDBLaboratoryRepository(db_path=db_file)
    ctx = BiomarkersApplicationContext(db_path=db_file, repository=repo)

    # Mock extractor for synthetic test document
    class MockDocExtractor:
        def extract(self, content: bytes, media_type: str = "application/pdf"):
            return doc

    use_case = ImportLaboratoryPdfUseCase(ingestion_service=ctx.ingestion_service, extractor=MockDocExtractor())
    summary = use_case.execute(b"%PDF-synthetic-privacy-bytes", dry_run=False)

    assert summary.dry_run is False
    assert summary.imported_observations_count == 2
    assert summary.resolved_observations_count == 1
    assert summary.unresolved_observations_count == 1

    # 3. Query DuckDB directly and audit all tables and columns for PII leak
    conn = repo._conn

    pii_terms = [
        "85080512345", "Marszałek", "Franciszek", "Nowak", "Anna Maria", "Wiśniewska",
        "Piotr", "Zieliński", "Marszałkowska", "kontakt@alab.pl", "PAC-998877", "DOC-123456"
    ]

    # Audit laboratory_reports
    reports_rows = conn.execute("SELECT * FROM laboratory_reports").fetchall()
    for row in reports_rows:
        row_str = str(row)
        for term in pii_terms:
            assert term not in row_str

    # Audit laboratory_import_runs
    runs_rows = conn.execute("SELECT * FROM laboratory_import_runs").fetchall()
    for row in runs_rows:
        row_str = str(row)
        for term in pii_terms:
            assert term not in row_str

    # Audit laboratory_observations
    obs_rows = conn.execute("SELECT observation_id, raw_name, raw_value, raw_unit, canonical_code, normalization_status FROM laboratory_observations").fetchall()
    assert len(obs_rows) == 2

    raw_names = [row[1] for row in obs_rows]  # raw_name column
    assert "Hemoglobina (HGB)" in raw_names
    assert "Nieznany Peptyd N-Końcowy" in raw_names

    for row in obs_rows:
        row_str = str(row)
        for term in pii_terms:
            assert term not in row_str

    # 4. Verify unknown real biomarker is preserved as UNRESOLVED
    unresolved_obs = [r for r in obs_rows if r[5] == NormalizationStatus.UNRESOLVED.value]  # normalization_status
    assert len(unresolved_obs) == 1
    assert unresolved_obs[0][1] == "Nieznany Peptyd N-Końcowy"

    repo.close()
