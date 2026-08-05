"""
Ingestion Pipeline, Extraction Ports, Ingestion Service, and Reprocessing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import uuid
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from biomarkers.deletion import DeletionMode
from biomarkers.errors import (
    EmptySourceDocumentError,
    LaboratoryIngestionError,
    ReportNotFoundError,
)
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
    create_laboratory_observation,
)
from biomarkers.registry import BiomarkerRegistry
from biomarkers.units import UnitNormalizer
from biomarkers.values import parse_laboratory_value


@dataclass(frozen=True)
class SourceDocumentIdentity:
    """Immutable identity header of an ingested binary source document."""

    source_document_hash: str
    byte_length: int
    media_type: str = "application/pdf"
    source_type: str = "pdf_text"
    original_filename_redacted: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.source_document_hash or not self.source_document_hash.strip():
            raise EmptySourceDocumentError("source_document_hash cannot be empty.")
        if self.byte_length <= 0:
            raise EmptySourceDocumentError("Source document byte length must be greater than zero.")


def calculate_source_document_hash(content: bytes) -> str:
    """
    Calculates deterministic SHA-256 digest of raw source document bytes.
    Rejects empty documents. Does NOT depend on file names. Does NOT log content.
    """
    if not content or len(content) == 0:
        raise EmptySourceDocumentError("Source document content cannot be empty.")
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class RawLaboratoryRow:
    """Immutable raw laboratory extraction row before normalization."""

    report_row_index: int
    raw_name: str
    raw_value: str
    raw_unit: str = ""
    raw_reference_text: Optional[str] = None
    raw_flag: Optional[str] = None
    collected_at: Optional[datetime] = None
    reported_at: Optional[datetime] = None
    laboratory_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.report_row_index < 0:
            raise ValueError("report_row_index must be >= 0.")
        if not self.raw_name or not self.raw_name.strip():
            raise ValueError("raw_name cannot be empty.")
        if not self.raw_value or not self.raw_value.strip():
            raise ValueError("raw_value cannot be empty.")


@dataclass(frozen=True)
class ExtractedDocument:
    """Immutable result of document extraction."""

    identity: SourceDocumentIdentity
    extracted_text: str
    raw_lines: Tuple[str, ...]
    metadata: Dict[str, Any] = field(default_factory=dict)


class LaboratoryDocumentExtractor(Protocol):
    """Protocol port for extracting text from source document bytes."""

    def extract(self, content: bytes, media_type: str = "application/pdf") -> ExtractedDocument: ...


class LaboratoryResultParser(Protocol):
    """Protocol port for parsing raw key-value rows from an extracted document."""

    def parse(self, extracted_document: ExtractedDocument) -> Tuple[RawLaboratoryRow, ...]: ...


# Synthetic adapters for testing pipeline (NOT in default composition root)
class SyntheticLaboratoryDocumentExtractor:
    """Synthetic test adapter for document extraction."""

    def extract(self, content: bytes, media_type: str = "application/pdf") -> ExtractedDocument:
        doc_hash = calculate_source_document_hash(content)
        identity = SourceDocumentIdentity(
            source_document_hash=doc_hash,
            byte_length=len(content),
            media_type=media_type,
            source_type="synthetic_pdf",
        )
        text = content.decode("utf-8", errors="replace")
        lines = tuple(line.strip() for line in text.splitlines() if line.strip())
        return ExtractedDocument(identity=identity, extracted_text=text, raw_lines=lines)


class SyntheticLaboratoryResultParser:
    """Synthetic test adapter for parsing raw laboratory rows."""

    def parse(self, extracted_document: ExtractedDocument) -> Tuple[RawLaboratoryRow, ...]:
        rows: List[RawLaboratoryRow] = []

        # Synthetic lines format: "ROW_INDEX | RAW_NAME | RAW_VALUE | RAW_UNIT | REF_TEXT"
        for idx, line in enumerate(extracted_document.raw_lines):
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    raw_name = parts[1] if len(parts) > 1 else parts[0]
                    raw_val = parts[2] if len(parts) > 2 else "1.0"
                    raw_unit = parts[3] if len(parts) > 3 else ""
                    ref_text = parts[4] if len(parts) > 4 else None

                    row = RawLaboratoryRow(
                        report_row_index=idx,
                        raw_name=raw_name,
                        raw_value=raw_val,
                        raw_unit=raw_unit,
                        raw_reference_text=ref_text,
                    )
                    rows.append(row)

        return tuple(rows)


@dataclass(frozen=True)
class LaboratoryIngestionRequest:
    """Immutable ingestion request payload."""

    content: bytes
    media_type: str = "application/pdf"
    source_type: str = "pdf_text"
    collected_at_fallback: Optional[datetime] = None
    reported_at_fallback: Optional[datetime] = None
    laboratory_name_fallback: Optional[str] = None
    parser_version: str = "1.0"
    extractor_version: str = "1.0"
    registry_version: str = "1.0"
    unit_rules_version: str = "1.0"


@dataclass(frozen=True)
class LaboratoryIngestionResult:
    """Immutable result of document ingestion processing."""

    report: Optional[LaboratoryReport]
    import_run: Optional[LaboratoryImportRun]
    observations: Tuple[LaboratoryObservation, ...]
    status: ImportRunStatus
    warnings: Tuple[str, ...]
    duplicate_document: bool
    requires_review_count: int
    unresolved_count: int
    possible_duplicate_count: int


class LaboratoryIngestionService:
    """
    Orchestrates the laboratory report ingestion pipeline:
    Document SHA-256 identity -> Extractor -> Parser -> BiomarkerRegistry match ->
    Value parsing -> UnitNormalizer -> Cross-report duplicate detection ->
    LaboratoryImportRun -> Atomic Repository persistence.
    """

    def __init__(
        self,
        extractor: LaboratoryDocumentExtractor,
        parser: LaboratoryResultParser,
        biomarker_registry: BiomarkerRegistry,
        unit_normalizer: UnitNormalizer,
        repository: Any,
        clock: Optional[Callable[[], datetime]] = None,
        id_generator: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.extractor = extractor
        self.parser = parser
        self.biomarker_registry = biomarker_registry
        self.unit_normalizer = unit_normalizer
        self.repository = repository
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.id_generator = id_generator or (lambda prefix: f"{prefix}-{uuid.uuid4().hex[:12]}")

    def ingest(self, request: LaboratoryIngestionRequest) -> LaboratoryIngestionResult:
        now = self.clock()
        doc_hash = calculate_source_document_hash(request.content)

        # 0. Tombstone Check: explicit tombstone check blocks automatic re-ingestion of deleted documents
        if self.repository.is_source_tombstoned(doc_hash):
            return LaboratoryIngestionResult(
                report=None,
                import_run=None,
                observations=(),
                status=ImportRunStatus.FAILED,
                warnings=("Source document was previously deleted with tombstone retention. Automatic re-ingestion is blocked.",),
                duplicate_document=True,
                requires_review_count=0,
                unresolved_count=0,
                possible_duplicate_count=0,
            )

        # 1. Idempotency Check: check if document hash already exists in repository
        existing_report = self.repository.find_report_by_source_hash(doc_hash)
        if existing_report:
            active_run = self.repository.get_active_import_run(existing_report.report_id)
            active_obs = active_run.observations if active_run else ()
            run_status = active_run.status if active_run else ImportRunStatus.COMPLETED
            return LaboratoryIngestionResult(
                report=existing_report,
                import_run=active_run,
                observations=active_obs,
                status=run_status,
                warnings=("Identical source document already ingested (SHA-256 duplicate).",),
                duplicate_document=True,
                requires_review_count=sum(1 for o in active_obs if o.requires_review),
                unresolved_count=sum(1 for o in active_obs if o.normalization_status == NormalizationStatus.UNRESOLVED),
                possible_duplicate_count=sum(1 for o in active_obs if o.is_possible_duplicate),
            )

        # 2. Extract Document & Parse Rows
        extracted_doc = self.extractor.extract(request.content, media_type=request.media_type)
        raw_rows = self.parser.parse(extracted_doc)

        report_id = self.id_generator("rep")
        import_run_id = self.id_generator("run")

        collected_at = request.collected_at_fallback or now
        reported_at = request.reported_at_fallback
        lab_name = request.laboratory_name_fallback

        # Create LaboratoryReport Header
        report = LaboratoryReport(
            report_id=report_id,
            collected_at=collected_at,
            source_type=request.source_type,
            source_document_hash=doc_hash,
            created_at=now,
            reported_at=reported_at,
            laboratory_name=lab_name,
        )

        observations: List[LaboratoryObservation] = []
        warnings: List[str] = []

        unresolved_cnt = 0
        review_cnt = 0
        possible_dup_cnt = 0

        # 3. Process Rows into LaboratoryObservations
        for row in raw_rows:
            try:
                obs_id = self.id_generator("obs")
                row_collected = row.collected_at or collected_at

                match = self.biomarker_registry.match_alias(
                    row.raw_name,
                    raw_unit=row.raw_unit,
                    raw_value=row.raw_value,
                )
                if match.normalization_status == NormalizationStatus.UNRESOLVED:
                    unresolved_cnt += 1

                if match.requires_review:
                    review_cnt += 1

                parsed_val = parse_laboratory_value(row.raw_value)

                unit_res = self.unit_normalizer.convert(
                    biomarker_code=match.canonical_code,
                    raw_numeric_value=parsed_val.numeric_value,
                    raw_unit=row.raw_unit,
                )

                # Check cross-report duplicate heuristic
                is_pos_dup = False
                if match.canonical_code and (parsed_val.numeric_value is not None or unit_res.normalized_value is not None):
                    dup_val = unit_res.normalized_value if unit_res.normalized_value is not None else parsed_val.numeric_value
                    existing_dups = self.repository.find_observations_for_duplicate_check(
                        canonical_code=match.canonical_code,
                        collected_at=row_collected,
                        normalized_value=dup_val,
                        exclude_report_id=report_id,
                    )
                    if existing_dups:
                        is_pos_dup = True
                        possible_dup_cnt += 1
                        warnings.append(
                            f"Observation for '{row.raw_name}' matches existing observation from another report on {row_collected.date()}."
                        )

                # Build Reference Range object if text provided
                ref_range = None
                if row.raw_reference_text:
                    ref_range = LaboratoryReferenceRange(text=row.raw_reference_text)

                obs = create_laboratory_observation(
                    observation_id=obs_id,
                    report_id=report_id,
                    import_run_id=import_run_id,
                    report_row_index=row.report_row_index,
                    raw_name=row.raw_name,
                    raw_value=row.raw_value,
                    raw_unit=row.raw_unit,
                    source_document_hash=doc_hash,
                    collected_at=row_collected,
                    parsed_value=parsed_val,
                    biomarker_match=match,
                    unit_result=unit_res,
                    laboratory_reference_range=ref_range,
                    laboratory_flag=row.raw_flag,
                    source_type=request.source_type,
                    laboratory_name=row.laboratory_name or lab_name,
                    is_possible_duplicate=is_pos_dup,
                )
                observations.append(obs)

            except Exception as e:
                warnings.append(f"Row {row.report_row_index} processing failed: {str(e)}")

        run_status = ImportRunStatus.COMPLETED
        if len(warnings) > 0 and len(observations) > 0:
            run_status = ImportRunStatus.PARTIAL
        elif len(observations) == 0 and len(raw_rows) > 0:
            run_status = ImportRunStatus.FAILED

        import_run = LaboratoryImportRun(
            import_run_id=import_run_id,
            report_id=report_id,
            parser_version=request.parser_version,
            extractor_version=request.extractor_version,
            registry_version=request.registry_version,
            unit_rules_version=request.unit_rules_version,
            started_at=now,
            completed_at=now,
            status=run_status,
            active=True,
            warnings=tuple(warnings),
            observations=tuple(observations),
        )

        # 4. Atomic Persistence & Activation
        self.repository.save_report_with_import_run(report, import_run)
        self.repository.activate_import_run(report_id, import_run_id)

        return LaboratoryIngestionResult(
            report=report,
            import_run=import_run,
            observations=tuple(observations),
            status=run_status,
            warnings=tuple(warnings),
            duplicate_document=False,
            requires_review_count=review_cnt,
            unresolved_count=unresolved_cnt,
            possible_duplicate_count=possible_dup_cnt,
        )

    def reprocess_report(
        self,
        report_id: str,
        content: bytes,
        parser_version: str = "2.0",
        extractor_version: str = "2.0",
        registry_version: str = "2.0",
        unit_rules_version: str = "2.0",
    ) -> LaboratoryIngestionResult:
        """
        Reprocesses an existing LaboratoryReport with new parser/registry versions.
        Creates a new LaboratoryImportRun, preserving historical runs.
        Activates the new run atomically. If reprocessing fails, previous active run is NOT deactivated.
        """
        now = self.clock()
        report = self.repository.get_report(report_id)
        if not report:
            raise ReportNotFoundError(f"Report '{report_id}' not found for reprocessing.")

        request = LaboratoryIngestionRequest(
            content=content,
            collected_at_fallback=report.collected_at,
            reported_at_fallback=report.reported_at,
            laboratory_name_fallback=report.laboratory_name,
            parser_version=parser_version,
            extractor_version=extractor_version,
            registry_version=registry_version,
            unit_rules_version=unit_rules_version,
        )

        extracted_doc = self.extractor.extract(content)
        raw_rows = self.parser.parse(extracted_doc)

        new_import_run_id = self.id_generator("run")
        observations: List[LaboratoryObservation] = []
        warnings: List[str] = []

        unresolved_cnt = 0
        review_cnt = 0
        possible_dup_cnt = 0

        for row in raw_rows:
            try:
                obs_id = self.id_generator("obs")
                row_collected = row.collected_at or report.collected_at

                match = self.biomarker_registry.match_alias(row.raw_name)
                if match.normalization_status == NormalizationStatus.UNRESOLVED:
                    unresolved_cnt += 1
                if match.requires_review:
                    review_cnt += 1

                parsed_val = parse_laboratory_value(row.raw_value)
                unit_res = self.unit_normalizer.convert(match.canonical_code, parsed_val.numeric_value, row.raw_unit)

                obs = create_laboratory_observation(
                    observation_id=obs_id,
                    report_id=report_id,
                    import_run_id=new_import_run_id,
                    report_row_index=row.report_row_index,
                    raw_name=row.raw_name,
                    raw_value=row.raw_value,
                    raw_unit=row.raw_unit,
                    source_document_hash=report.source_document_hash,
                    collected_at=row_collected,
                    parsed_value=parsed_val,
                    biomarker_match=match,
                    unit_result=unit_res,
                )
                observations.append(obs)
            except Exception as e:
                warnings.append(f"Reprocessing row {row.report_row_index} failed: {str(e)}")

        run_status = ImportRunStatus.COMPLETED if len(warnings) == 0 else ImportRunStatus.PARTIAL

        new_run = LaboratoryImportRun(
            import_run_id=new_import_run_id,
            report_id=report_id,
            parser_version=parser_version,
            extractor_version=extractor_version,
            registry_version=registry_version,
            unit_rules_version=unit_rules_version,
            started_at=now,
            completed_at=now,
            status=run_status,
            active=False,  # Set active via atomic activation below
            warnings=tuple(warnings),
            observations=tuple(observations),
        )

        # Save new run and atomically activate it
        self.repository.save_report_with_import_run(report, new_run)
        self.repository.activate_import_run(report_id, new_import_run_id)

        active_run = self.repository.get_active_import_run(report_id)

        return LaboratoryIngestionResult(
            report=report,
            import_run=active_run,
            observations=tuple(observations),
            status=run_status,
            warnings=tuple(warnings),
            duplicate_document=False,
            requires_review_count=review_cnt,
            unresolved_count=unresolved_cnt,
            possible_duplicate_count=possible_dup_cnt,
        )
