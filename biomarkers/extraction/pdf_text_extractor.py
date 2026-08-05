"""
Production Adapter for Text PDF Document Extraction using pypdf.
"""

from dataclasses import dataclass
import io

from biomarkers.extraction.errors import InvalidPdfDocumentError, PdfTextLayerUnavailableError
from biomarkers.ingestion import calculate_source_document_hash


@dataclass(frozen=True)
class ExtractedLaboratoryPage:
    """Immutable extracted page representation."""

    page_number: int
    text: str
    extraction_confidence: float = 1.0
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be >= 1")


@dataclass(frozen=True)
class ExtractedLaboratoryDocument:
    """Immutable extracted PDF document payload."""

    source_document_hash: str
    page_count: int
    pages: tuple[ExtractedLaboratoryPage, ...]
    extractor_version: str = "1.0"
    warnings: tuple[str, ...] = ()
    text_layer_available: bool = True

    def __post_init__(self) -> None:
        if self.page_count < 0:
            raise ValueError("page_count cannot be negative")


class PdfTextLaboratoryDocumentExtractor:
    """
    Production adapter extracting text layer from digital PDF lab reports.
    Rejects scanned image PDFs requiring OCR and invalid or empty content.
    """

    def __init__(self, extractor_version: str = "1.0") -> None:
        self.extractor_version = extractor_version

    def extract(self, content: bytes, media_type: str = "application/pdf") -> ExtractedLaboratoryDocument:
        """
        Extracts text per page from PDF bytes.
        Does NOT store text to disk or log document contents.
        """
        if not content:
            raise InvalidPdfDocumentError("Source PDF document content is empty.")

        if not content.startswith(b"%PDF"):
            raise InvalidPdfDocumentError("Source document is not a valid PDF file (missing %PDF header).")

        doc_hash = calculate_source_document_hash(content)

        try:
            import pypdf
        except ImportError:
            raise InvalidPdfDocumentError("PDF extraction library (pypdf) is not available.")

        try:
            stream = io.BytesIO(content)
            reader = pypdf.PdfReader(stream)
            page_count = len(reader.pages)
        except Exception as err:
            raise InvalidPdfDocumentError(f"Failed to parse PDF document structure: {type(err).__name__}") from err

        if page_count == 0:
            raise InvalidPdfDocumentError("PDF document contains 0 pages.")

        pages_list: list[ExtractedLaboratoryPage] = []
        total_text_len = 0
        doc_warnings: list[str] = []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            try:
                raw_page_text = page.extract_text() or ""
            except Exception:
                raw_page_text = ""
                doc_warnings.append(f"Failed to extract text from page {page_num}.")

            stripped_text = raw_page_text.strip()
            total_text_len += len(stripped_text)

            pages_list.append(
                ExtractedLaboratoryPage(
                    page_number=page_num,
                    text=raw_page_text,
                    extraction_confidence=1.0 if stripped_text else 0.0,
                    warnings=(),
                )
            )

        if total_text_len == 0:
            raise PdfTextLayerUnavailableError(
                "PDF document does not contain a readable text layer. OCR is required but not enabled."
            )

        return ExtractedLaboratoryDocument(
            source_document_hash=doc_hash,
            page_count=page_count,
            pages=tuple(pages_list),
            extractor_version=self.extractor_version,
            warnings=tuple(doc_warnings),
            text_layer_available=True,
        )
