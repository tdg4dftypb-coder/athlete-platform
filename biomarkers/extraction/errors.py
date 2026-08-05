"""
Controlled Exceptions for Biomarkers Extraction Subsystem.
Enforces privacy-safe exception messages without health value or filepath leakage.
"""

from biomarkers.errors import BiomarkersError


class LaboratoryExtractionError(BiomarkersError):
    """Base class for all extraction errors."""
    pass


class InvalidPdfDocumentError(LaboratoryExtractionError):
    """Raised when provided content is empty, corrupted, or not a valid PDF file."""
    pass


class PdfTextLayerUnavailableError(LaboratoryExtractionError):
    """Raised when PDF lacks a readable text layer (scanned image requiring OCR)."""
    pass


class UnsupportedLaboratoryReportError(LaboratoryExtractionError):
    """Raised when laboratory report layout is not recognized by available parsers."""
    pass


class LaboratoryReportParseError(LaboratoryExtractionError):
    """Raised when report parsing fails due to structural or formatting errors."""
    pass


class LaboratoryPdfImportError(LaboratoryExtractionError):
    """Raised when overall PDF import orchestration fails."""
    pass
