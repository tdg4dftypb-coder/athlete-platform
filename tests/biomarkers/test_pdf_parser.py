"""
Unit Test Suite for Text Laboratory Report Parser (Sprint 7B).
"""

from datetime import datetime, timezone

from biomarkers.extraction.pdf_text_extractor import ExtractedLaboratoryDocument, ExtractedLaboratoryPage
from biomarkers.parsing.text_report_parser import TextLaboratoryReportParser


def test_parser_pipe_separated_table() -> None:
    text_page = """
    Laboratorium Synevo Warszawa
    Data pobrania: 05.08.2026 08:30
    Badanie | Wynik | Jednostka | Zakres referencyjny | Flaga
    Glukoza | 92.5 | mg/dL | 70 - 99 |
    Ferrytyna | 14,2 | µg/L | 30.0 - 200.0 | L
    TSH | < 0.01 | mIU/L | 0.27 - 4.20 |
    Nierozpoznany Marker | 55 | U/mL | 0 - 100 | H
    Strona 1 z 1
    """

    doc = ExtractedLaboratoryDocument(
        source_document_hash="hash-parser-001",
        page_count=1,
        pages=(ExtractedLaboratoryPage(page_number=1, text=text_page),),
    )

    parser = TextLaboratoryReportParser()
    rows = parser.parse(doc)
    header = parser.last_parsed_header

    assert header is not None
    assert header.laboratory_name == "Synevo"
    assert header.collected_at == datetime(2026, 8, 5, 8, 30, tzinfo=timezone.utc)
    assert len(rows) == 4

    r1, r2, r3, r4 = rows

    # Row 1: Glukoza
    assert r1.raw_name == "Glukoza"
    assert r1.raw_value == "92.5"
    assert r1.raw_unit == "mg/dL"

    # Row 2: Ferrytyna (comma decimal, flag L)
    assert r2.raw_name == "Ferrytyna"
    assert r2.raw_value == "14,2"
    assert r2.raw_unit == "µg/L"
    assert r2.raw_flag == "L"

    # Row 3: TSH (inequality)
    assert r3.raw_name == "TSH"
    assert r3.raw_value == "< 0.01"

    # Row 4: Unknown Marker
    assert r4.raw_name == "Nierozpoznany Marker"
    assert r4.raw_value == "55"
    assert r4.raw_flag == "H"


def test_parser_regex_and_wrapped_lines() -> None:
    text_page = """
    Diagnostyka Sp. z o.o.
    Data pobrania: 2026-08-05
    Badanie Wynik Jednostka Zakres Flaga
    Glukoza 92,5 mg/dL 70-99
    Witamina D
    (25-OH) 34,5 ng/mL 30-100
    CRP < 0.1 mg/L < 5.0
    Strona 1 z 1
    """

    doc = ExtractedLaboratoryDocument(
        source_document_hash="hash-parser-002",
        page_count=1,
        pages=(ExtractedLaboratoryPage(page_number=1, text=text_page),),
    )

    parser = TextLaboratoryReportParser()
    rows = parser.parse(doc)
    header = parser.last_parsed_header

    assert header is not None
    assert header.laboratory_name == "Diagnostyka"
    assert header.collected_at == datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc)
    assert len(rows) >= 3

    row_names = [r.raw_name for r in rows]
    assert any("Glukoza" in n for n in row_names)
    assert any("Witamina D (25-OH)" in n for n in row_names)
    assert any("CRP" in n for n in row_names)


def test_parser_missing_collected_at_warning() -> None:
    text_page = """
    ALAB laboratoria
    Data wydruku: 05.08.2026
    Glukoza | 90 | mg/dL | 70-99 |
    """

    doc = ExtractedLaboratoryDocument(
        source_document_hash="hash-parser-003",
        page_count=1,
        pages=(ExtractedLaboratoryPage(page_number=1, text=text_page),),
    )

    parser = TextLaboratoryReportParser()
    rows = parser.parse(doc)
    header = parser.last_parsed_header

    assert header is not None
    assert header.collected_at is None
    assert len(header.warnings) > 0
    assert "collected_at" in header.warnings[0]
