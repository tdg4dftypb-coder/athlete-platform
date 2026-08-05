"""
Unit Test Suite for Text PDF Laboratory Document Extractor (Sprint 7B).
"""

import io
import pytest
import pypdf

from biomarkers.extraction import (
    ExtractedLaboratoryDocument,
    InvalidPdfDocumentError,
    PdfTextLaboratoryDocumentExtractor,
    PdfTextLayerUnavailableError,
)


def create_synthetic_pdf(text_lines: list[str]) -> bytes:
    """Generates a valid minimal synthetic PDF in memory with text content."""
    stream_content = "\n".join(f"BT /F1 12 Tf 50 {700 - idx * 20} Td ({line}) Tj ET" for idx, line in enumerate(text_lines))
    stream_bytes = stream_content.encode("utf-8")
    stream_len = len(stream_bytes)

    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj\n"
        b"4 0 obj <</Length " + str(stream_len).encode("utf-8") + b">>\nstream\n"
        + stream_bytes + b"\nendstream\nendobj\n"
        b"5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer <</Size 6 /Root 1 0 R>>\nstartxref\n300\n%%EOF\n"
    )
    return pdf


def create_scanned_image_pdf() -> bytes:
    """Generates a valid PDF with an empty page (no text layer, simulating image scan)."""
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R>> endobj\n"
        b"4 0 obj <</Length 0>>\nstream\n\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer <</Size 5 /Root 1 0 R>>\nstartxref\n200\n%%EOF\n"
    )
    return pdf


def test_pdf_extractor_valid_text() -> None:
    pdf_bytes = create_synthetic_pdf(["Glukoza 92.5 mg/dL 70-99", "Ferrytyna 14.2 ug/L 30-200"])
    extractor = PdfTextLaboratoryDocumentExtractor()
    doc = extractor.extract(pdf_bytes)

    assert isinstance(doc, ExtractedLaboratoryDocument)
    assert doc.page_count == 1
    assert len(doc.pages) == 1
    assert doc.text_layer_available is True
    assert "Glukoza" in doc.pages[0].text
    assert "Ferrytyna" in doc.pages[0].text


def test_pdf_extractor_empty_content() -> None:
    extractor = PdfTextLaboratoryDocumentExtractor()
    with pytest.raises(InvalidPdfDocumentError, match="empty"):
        extractor.extract(b"")


def test_pdf_extractor_non_pdf() -> None:
    extractor = PdfTextLaboratoryDocumentExtractor()
    with pytest.raises(InvalidPdfDocumentError, match="not a valid PDF"):
        extractor.extract(b"Hello World, not a PDF content")


def test_pdf_extractor_scanned_image_no_text_layer() -> None:
    pdf_bytes = create_scanned_image_pdf()
    extractor = PdfTextLaboratoryDocumentExtractor()
    with pytest.raises(PdfTextLayerUnavailableError, match="OCR is required"):
        extractor.extract(pdf_bytes)


def test_pdf_extractor_corrupted_pdf() -> None:
    extractor = PdfTextLaboratoryDocumentExtractor()
    with pytest.raises(InvalidPdfDocumentError):
        extractor.extract(b"%PDF-1.4\ncorrupted bytes content without pdf structure")
