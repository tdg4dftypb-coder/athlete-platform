"""
Regression Test Suite for ALAB Laboratory Report Parser and Biomarker Registry (Sprint 7C.1).
"""

from datetime import datetime, timezone
import pytest

from biomarkers.extraction.pdf_text_extractor import ExtractedLaboratoryDocument, ExtractedLaboratoryPage
from biomarkers.models import NormalizationStatus
from biomarkers.parsing.alab_report_parser import AlabTextLaboratoryReportParser
from biomarkers.registry import create_default_biomarker_registry
from biomarkers.use_cases.import_pdf import ImportLaboratoryPdfUseCase, PdfImportSummary


def build_synthetic_alab_doc() -> ExtractedLaboratoryDocument:
    text_page_1 = """
    ALAB laboratoria Sp. z o.o.
    Punkt Pobrań: Warszawa
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
    Nierozpoznany Test Laboratoryjny 12,5 U/L 0 — 10
    Komentarz: Wyniki skonsultowano z lekarzem w leczeniu antagonistami witaminy K.
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

    # Confirm key required markers are resolved properly
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

    # Confirm unresolved items remain isolated without crash
    assert any("Nierozpoznany Test" in name for name in unresolved_names)


def test_accounting_invariant_and_line_counters() -> None:
    doc = build_synthetic_alab_doc()
    parser = AlabTextLaboratoryReportParser()
    rows = parser.parse(doc)
    header = parser.last_parsed_header

    assert header.candidate_rows_count > 0
    assert header.extracted_rows_count == len(rows)
    assert header.ignored_lines_count > 0
    assert header.failed_rows_count == 0


def test_hbs_numeric_and_qualitative_dual_observations() -> None:
    doc = build_synthetic_alab_doc()
    parser = AlabTextLaboratoryReportParser()
    rows = parser.parse(doc)
    registry = create_default_biomarker_registry()

    hbs_matches = [
        registry.match_alias(r.raw_name, raw_unit=r.raw_unit, raw_value=r.raw_value)
        for r in rows if "hbs" in r.raw_name.lower()
    ]

    assert len(hbs_matches) == 2
    codes = [m.canonical_code for m in hbs_matches]
    assert "hbs_antigen_numeric" in codes
    assert "hbs_antigen_qualitative" in codes


def test_rdw_cv_and_rdw_sd_differentiation() -> None:
    doc = build_synthetic_alab_doc()
    parser = AlabTextLaboratoryReportParser()
    rows = parser.parse(doc)
    registry = create_default_biomarker_registry()

    rdw_matches = [
        registry.match_alias(r.raw_name, raw_unit=r.raw_unit, raw_value=r.raw_value)
        for r in rows if "rdw" in r.raw_name.lower()
    ]

    assert len(rdw_matches) == 2
    codes = [m.canonical_code for m in rdw_matches]
    assert "rdw_cv" in codes
    assert "rdw_sd" in codes


def test_ignored_comment_not_imported() -> None:
    doc = build_synthetic_alab_doc()
    parser = AlabTextLaboratoryReportParser()
    rows = parser.parse(doc)

    for r in rows:
        assert "skonsultowano z lekarzem" not in r.raw_name
        assert "zatwierdził" not in r.raw_name.lower()
        assert "sysmex" not in r.raw_name.lower()


def test_alab_header_collection_date_logic() -> None:
    parser = AlabTextLaboratoryReportParser()

    # Case 1: Single date
    doc_1 = ExtractedLaboratoryDocument(
        source_document_hash="hash-date-1",
        page_count=1,
        pages=(ExtractedLaboratoryPage(page_number=1, text="ALAB laboratoria\ndata i godz. pobrania: 05-08-2026 08:30\nGlukoza 90 mg/dL 70-99"),),
    )
    parser.parse(doc_1)
    assert parser.last_parsed_header.collected_at == datetime(2026, 8, 5, 8, 30, tzinfo=timezone.utc)

    # Case 2: Repeated identical dates across sections
    doc_2 = ExtractedLaboratoryDocument(
        source_document_hash="hash-date-2",
        page_count=2,
        pages=(
            ExtractedLaboratoryPage(page_number=1, text="ALAB\ndata i godz. pobrania: 05-08-2026 08:30\nGlukoza 90 mg/dL"),
            ExtractedLaboratoryPage(page_number=2, text="ALAB\ndata i godz. pobrania: 05-08-2026 08:30\nTSH 1.2 mIU/L"),
        ),
    )
    parser.parse(doc_2)
    assert parser.last_parsed_header.collected_at == datetime(2026, 8, 5, 8, 30, tzinfo=timezone.utc)

    # Case 3: Multiple conflicting dates
    doc_3 = ExtractedLaboratoryDocument(
        source_document_hash="hash-date-3",
        page_count=2,
        pages=(
            ExtractedLaboratoryPage(page_number=1, text="ALAB\ndata i godz. pobrania: 05-08-2026 08:30\nGlukoza 90 mg/dL"),
            ExtractedLaboratoryPage(page_number=2, text="ALAB\ndata i godz. pobrania: 06-08-2026 14:00\nTSH 1.2 mIU/L"),
        ),
    )
    parser.parse(doc_3)
    assert parser.last_parsed_header.collected_at is None
    assert "Multiple different collection dates" in parser.last_parsed_header.warnings[0]
