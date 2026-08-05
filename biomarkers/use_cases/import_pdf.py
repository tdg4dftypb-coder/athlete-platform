"""
Use Case Orchestrating Text PDF Laboratory Import for Biomarkers Domain.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

from biomarkers.extraction import (
    ExtractedLaboratoryDocument,
    PdfTextLaboratoryDocumentExtractor,
)
from biomarkers.ingestion import (
    LaboratoryIngestionRequest,
    LaboratoryIngestionResult,
    LaboratoryIngestionService,
)
from biomarkers.models import ImportRunStatus
from biomarkers.parsing import ParsedReportHeader, TextLaboratoryReportParser
from biomarkers.repository import InMemoryLaboratoryRepository, LaboratoryRepository


@dataclass(frozen=True)
class PdfImportSummary:
    """Immutable, privacy-safe summary of PDF import execution."""

    report_id: Optional[str]
    import_run_id: Optional[str]
    status: ImportRunStatus
    page_count: int
    extracted_rows_count: int
    imported_observations_count: int
    unresolved_observations_count: int
    possible_duplicates_count: int
    warnings: Tuple[str, ...]
    dry_run: bool = False
    duplicate_document: bool = False


class ImportLaboratoryPdfUseCase:
    """
    Use case orchestrating text PDF extraction, parsing, biomarker alias matching,
    unit normalization, and atomic persistence into LaboratoryRepository.
    """

    def __init__(
        self,
        ingestion_service: LaboratoryIngestionService,
        extractor: Optional[PdfTextLaboratoryDocumentExtractor] = None,
        parser: Optional[TextLaboratoryReportParser] = None,
    ) -> None:
        self.extractor = extractor or PdfTextLaboratoryDocumentExtractor()
        self.parser = parser or TextLaboratoryReportParser()
        self.ingestion_service = ingestion_service
        # Configure ingestion service to use text PDF extractor and parser ports
        self.ingestion_service.extractor = self.extractor
        self.ingestion_service.parser = self.parser

    def execute(
        self,
        pdf_content: bytes,
        laboratory_name_override: Optional[str] = None,
        collected_at_override: Optional[datetime] = None,
        dry_run: bool = False,
    ) -> PdfImportSummary:
        """
        Executes end-to-end PDF lab import.
        If dry_run is True, performs extraction, parsing, alias matching, and unit normalization
        without creating records in the persistent database.
        """
        # 1. Extract PDF Text Layer
        extracted_doc = self.extractor.extract(pdf_content)

        # 2. Parse Raw Laboratory Rows
        raw_rows = self.parser.parse(extracted_doc)
        header: ParsedReportHeader = getattr(self.parser, "last_parsed_header", None) or ParsedReportHeader()

        lab_name = laboratory_name_override or header.laboratory_name
        collected_at = collected_at_override or header.collected_at

        warnings_list = list(extracted_doc.warnings) + list(header.warnings)

        if not raw_rows:
            warnings_list.append("No laboratory result rows could be extracted from document text layer.")

        # 3. Handle Dry Run vs Persistent Ingestion
        if dry_run:
            transient_repo = InMemoryLaboratoryRepository()
            dry_service = LaboratoryIngestionService(
                repository=transient_repo,
                biomarker_registry=self.ingestion_service.biomarker_registry,
                unit_normalizer=self.ingestion_service.unit_normalizer,
                extractor=self.extractor,
                parser=self.parser,
                clock=self.ingestion_service.clock,
            )
            req = LaboratoryIngestionRequest(
                content=pdf_content,
                media_type="application/pdf",
                source_type="pdf_digital",
                collected_at_fallback=collected_at,
                reported_at_fallback=header.reported_at,
                laboratory_name_fallback=lab_name,
            )
            res = dry_service.ingest(req)
            return PdfImportSummary(
                report_id="dry-run",
                import_run_id="dry-run",
                status=res.status,
                page_count=extracted_doc.page_count,
                extracted_rows_count=len(raw_rows),
                imported_observations_count=len(res.observations),
                unresolved_observations_count=res.unresolved_count,
                possible_duplicates_count=res.possible_duplicate_count,
                warnings=tuple(warnings_list + list(res.warnings)),
                dry_run=True,
                duplicate_document=res.duplicate_document,
            )

        # Persistent Ingestion
        req = LaboratoryIngestionRequest(
            content=pdf_content,
            media_type="application/pdf",
            source_type="pdf_digital",
            collected_at_fallback=collected_at,
            reported_at_fallback=header.reported_at,
            laboratory_name_fallback=lab_name,
        )

        res = self.ingestion_service.ingest(req)

        return PdfImportSummary(
            report_id=res.report.report_id if res.report else None,
            import_run_id=res.import_run.import_run_id if res.import_run else None,
            status=res.status,
            page_count=extracted_doc.page_count,
            extracted_rows_count=len(raw_rows),
            imported_observations_count=len(res.observations),
            unresolved_observations_count=res.unresolved_count,
            possible_duplicates_count=res.possible_duplicate_count,
            warnings=tuple(warnings_list + list(res.warnings)),
            dry_run=False,
            duplicate_document=res.duplicate_document,
        )
