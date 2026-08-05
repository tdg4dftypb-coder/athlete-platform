"""
Regression Test Suite for ALAB Laboratory Report Parser, PII Filtering, and Row Qualification (Sprint 7C.2).
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from biomarkers.composition import BiomarkersApplicationContext
from biomarkers.extraction.pdf_text_extractor import ExtractedLaboratoryDocument, ExtractedLaboratoryPage
from biomarkers.models import NormalizationStatus
from biomarkers.parsing.alab_report_parser import AlabTextLaboratoryReportParser
from biomarkers.parsing.row_qualifier import LaboratoryResultRowQualifier, RowQualificationStatus
from biomarkers.persistence.duckdb_repository import DuckDBLaboratoryRepository
from biomarkers.registry import create_default_biomarker_registry
from biomarkers.use_cases.import_pdf import ImportLaboratoryPdfUseCase, PdfImportSummary


def build_synthetic_alab_doc() -> ExtractedLaboratoryDocument:
    text_page_1 = """
    ALAB laboratoria Sp. z o.o.
    ul. Marszałkowska 10/15, 00-001 Warszawa
    Punkt Pobrań: Warszawa
    Pacjent: Marszałek Jan Kowalski
    PESEL: 85080512345
    Adres: ul. Marszałkowska 10/15, Warszawa
    Ident. pacjenta: PAC-998877
    Ident. dokumentu: DOC-123456
    Lekarz zlecający: dr med. Franciszek Nowak
    data i godz. pobrania: 05-08-2026 08:30
    Badanie Wynik Jednostka Zakres referencyjny Flaga
    Morfologia krwi
    Leukocyty (WBC) 6.45 10^3/µL 4.00 - 10.00
    Erytrocyty (RBC) 4.82 10^6/µL 4.20 - 5.40
    Hemoglobina (HGB) 14.8 g/dL 12.0 - 16.0
    Hematokryt (HCT) 44.2 % 37.0 - 47.0
    Wskaźnik MCV 91.7 fL 80.0 - 98.0
    Wskaźnik MCH 30.7 pg 27.0 - 33.0
    Wskaźnik MCHC 33.5 g/dL 31.0 - 36.0
    RDW-CV 12.4 % 11.5 - 14.5
    RDW-SD 42.1 fL 37.0 - 47.0
    Płytki krwi (PLT) 245 10^3/µL 150 - 400
    Hematokryt płytkowy (PCT) 0.24 % 0.10 - 0.40
    Średnia objętość płytki (MPV) 9.8 fL 7.2 - 11.1
    Duże płytki (P-LCR) 22.5 % 13.0 - 43.0
    Neutrofile % 58.2 % 40.0 - 70.0
    Limfocyty % 30.1 % 20.0 - 45.0
    Monocyty % 7.5 % 2.0 - 10.0
    Eozynofile % 3.4 % 1.0 - 5.0
    Bazofile % 0.5 % 0.0 - 1.0
    Granulocyty niedojrzałe % 0.3 % 0.0 - 0.5
    Neutrofile # 3.75 10^3/µL 1.80 - 7.00
    Limfocyty # 1.94 10^3/µL 1.00 - 4.50
    Monocyty # 0.48 10^3/µL 0.10 - 1.00
    Eozynofile # 0.22 10^3/µL 0.00 - 0.50
    Bazofile # 0.03 10^3/µL 0.00 - 0.20
    Granulocyty niedojrzałe # 0.02 10^3/µL 0.00 - 0.05
    Analizator: Sysmex XN
    Metoda: Spektrofotometria / Przepływowa
    Strona 1 z 2
    """

    text_page_2 = """
    ALAB laboratoria Sp. z o.o.
    data i godz. pobrania: 05-08-2026 08:30
    Badanie Wynik Jednostka Zakres referencyjny Flaga
    Układ krzepnięcia
    Czas kaolinowo-kefalinowy (APTT)
    28,6 sek 25,4 — 36,9
    Czas protrombinowy (PT), INR/
    Czas protrombinowy (PT) 11,2 sek 9,4 — 12,5
    Wskaźnik protrombinowy 98,5 % 80,0 — 120,0
    INR 1,02
    D-dimer FEU < 500 ng/mL FEU < 500
    HBs - antygen HBs (WZW typu B) (V39) 0,37 S/CO Instrukcja Abbott
    HBs - antygen HBs (WZW typu B) nieobecny
    Nieznany Peptyd N-Końcowy 12,5 U/L 0 — 10
    Komentarz: Wyniki skonsultowano z lekarzem w leczeniu antagonistami witaminy K.
    Autoryzował: mgr Diagnosta Jan Kowalski
    Zatwierdził: Diagnosta mgr Jan Kowalski
    Strona 2 z 2
    """

    return ExtractedLaboratoryDocument(
        source_document_hash="hash-alab-synthetic-001",
        page_count=2,
        pages=(
            ExtractedLaboratoryPage(page_number=1, text=text_page_1),
            ExtractedLaboratoryPage(page_number=2, text=text_page_2),
        ),
    )


def test_alab_parser_synthetic_fixture_full_flow() -> None:
    doc = build_synthetic_alab_doc()

    parser = AlabTextLaboratoryReportParser()
    assert parser.can_parse(doc) is True

    rows = parser.parse(doc)
    header = parser.last_parsed_header

    assert header is not None
    assert header.laboratory_name == "ALAB laboratoria"
    assert header.collected_at == datetime(2026, 8, 5, 8, 30, tzinfo=timezone.utc)

    # Validate row extraction and mapping against registry
    registry = create_default_biomarker_registry()
    matched_codes = []
    unresolved_names = []

    for r in rows:
        match = registry.match_alias(r.raw_name, raw_unit=r.raw_unit, raw_value=r.raw_value)
        if match.canonical_code:
            matched_codes.append(match.canonical_code)
        else:
            unresolved_names.append(r.raw_name)

    assert "leukocytes" in matched_codes
    assert "aptt" in matched_codes
    assert "prothrombin_time" in matched_codes
    assert "prothrombin_index" in matched_codes
    assert "inr" in matched_codes
    assert "d_dimer" in matched_codes
    assert "hbs_antigen_numeric" in matched_codes
    assert "hbs_antigen_qualitative" in matched_codes
    assert "rdw_cv" in matched_codes
    assert "rdw_sd" in matched_codes

    # Real unknown biomarker is preserved cleanly as UNRESOLVED
    assert unresolved_names == ["Nieznany Peptyd N-Końcowy"]


def test_accounting_invariant_and_line_counters() -> None:
    doc = build_synthetic_alab_doc()
    parser = AlabTextLaboratoryReportParser()
    rows = parser.parse(doc)
    header = parser.last_parsed_header

    assert header.candidate_rows_count > 0
    assert header.extracted_rows_count == len(rows)
    assert header.ignored_lines_count > 0
    assert header.failed_rows_count == 0


def test_pesel_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res = qualifier.qualify("PESEL: 85080512345")
    assert res.status == RowQualificationStatus.IGNORED_PII_ADMIN


def test_address_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res = qualifier.qualify("Adres: ul. Marszałkowska 10/15, 00-001 Warszawa")
    assert res.status == RowQualificationStatus.IGNORED_PII_ADMIN


def test_patient_id_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res_1 = qualifier.qualify("Ident. pacjenta: PAC-998877")
    res_2 = qualifier.qualify("Pacjent: Kowalski Jan")
    assert res_1.status == RowQualificationStatus.IGNORED_PII_ADMIN
    assert res_2.status == RowQualificationStatus.IGNORED_PII_ADMIN


def test_ordering_clinician_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res = qualifier.qualify("Lekarz zlecający: dr med. Franciszek Nowak")
    assert res.status == RowQualificationStatus.IGNORED_PII_ADMIN


def test_laboratory_diagnostician_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res_1 = qualifier.qualify("Autoryzował: mgr Diagnosta Anna Nowak")
    res_2 = qualifier.qualify("Zatwierdzili: mgr Diagnosta Piotr Zieliński")
    assert res_1.status == RowQualificationStatus.IGNORED_PII_ADMIN
    assert res_2.status == RowQualificationStatus.IGNORED_PII_ADMIN


def test_footer_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res_1 = qualifier.qualify("Strona 1 z 2")
    res_2 = qualifier.qualify("ALAB laboratoria Sp. z o.o. tel. +48 22 349 60 12")
    assert res_1.status == RowQualificationStatus.IGNORED_PII_ADMIN
    assert res_2.status == RowQualificationStatus.IGNORED_PII_ADMIN


def test_page_header_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res = qualifier.qualify("Badanie Wynik Jednostka Zakres referencyjny Flaga")
    assert res.status == RowQualificationStatus.IGNORED_NOISE_HEADER


def test_method_analyzer_ignored() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res_1 = qualifier.qualify("Analizator: Sysmex XN")
    res_2 = qualifier.qualify("Metoda: Spektrofotometria")
    assert res_1.status == RowQualificationStatus.IGNORED_PII_ADMIN
    assert res_2.status == RowQualificationStatus.IGNORED_PII_ADMIN


def test_clinical_comment_ignored() -> None:
    doc = build_synthetic_alab_doc()
    parser = AlabTextLaboratoryReportParser()
    rows = parser.parse(doc)

    for r in rows:
        assert "skonsultowano z lekarzem" not in r.raw_name
        assert "zatwierdził" not in r.raw_name.lower()


def test_real_unknown_biomarker_to_unresolved() -> None:
    doc = build_synthetic_alab_doc()
    parser = AlabTextLaboratoryReportParser()
    rows = parser.parse(doc)
    registry = create_default_biomarker_registry()

    unknown_row = [r for r in rows if r.raw_name == "Nieznany Peptyd N-Końcowy"]
    assert len(unknown_row) == 1

    match = registry.match_alias(unknown_row[0].raw_name)
    assert match.normalization_status == NormalizationStatus.UNRESOLVED
    assert match.canonical_code is None


def test_qualitative_result_to_observation() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res = qualifier.qualify("HBs - antygen HBs (WZW typu B) nieobecny")
    assert res.status == RowQualificationStatus.QUALIFIED_RESULT


def test_inr_without_unit_to_observation() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res = qualifier.qualify("INR 1,02")
    assert res.status == RowQualificationStatus.QUALIFIED_RESULT


def test_multiline_aptt_to_observation() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res_line1 = qualifier.qualify("Czas kaolinowo-kefalinowy (APTT) (G11)")
    assert res_line1.reason_code == "MULTILINE_NAME_BUFFER"

    res_line2 = qualifier.qualify("28,6 sek 25,4 — 36,9", pending_name="Czas kaolinowo-kefalinowy (APTT) (G11)")
    assert res_line2.status == RowQualificationStatus.QUALIFIED_RESULT


def test_no_pii_in_warnings() -> None:
    qualifier = LaboratoryResultRowQualifier()
    res = qualifier.qualify("PESEL: 85080512345")
    assert res.reason_code == "NON_RESULT_LINE_IGNORED"
    assert "85080512345" not in res.reason_code


def test_no_pii_in_duckdb(tmp_path: Path) -> None:
    db_file = str(tmp_path / "test_no_pii.duckdb")
    doc = build_synthetic_alab_doc()

    repo = DuckDBLaboratoryRepository(db_path=db_file)
    ctx = BiomarkersApplicationContext(db_path=db_file, repository=repo)

    class MockExtractor:
        def extract(self, content: bytes, media_type: str = "application/pdf"):
            return doc

    use_case = ImportLaboratoryPdfUseCase(ingestion_service=ctx.ingestion_service, extractor=MockExtractor())
    summary = use_case.execute(b"%PDF-synthetic-test", dry_run=False)

    conn = repo._conn

    pii_strings = ["85080512345", "Marszałek Jan Kowalski", "Franciszek Nowak", "Piotr Zieliński", "Marszałkowska"]

    for table in ["laboratory_reports", "laboratory_import_runs", "laboratory_observations"]:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        for r in rows:
            r_str = str(r)
            for pii in pii_strings:
                assert pii not in r_str

    repo.close()
