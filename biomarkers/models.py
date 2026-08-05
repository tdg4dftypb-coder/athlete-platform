"""
Pure domain models and value objects for Biomarkers & Laboratory Intelligence.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import re
from typing import Any, Dict, Optional, Tuple

from biomarkers.errors import (
    InvalidBiomarkerDefinitionError,
    InvalidImportRunError,
    InvalidLaboratoryObservationError,
)


class BiomarkerCategory(Enum):
    MORPHOLOGY = "morphology"
    IRON_PANEL = "iron_panel"
    HORMONES = "hormones"
    LIPIDS = "lipids"
    VITAMINS = "vitamins"
    ELECTROLYTES = "electrolytes"
    INFLAMMATORY_MARKERS = "inflammatory_markers"
    URINALYSIS = "urinalysis"
    OTHER = "other"


class BiomarkerValueType(Enum):
    NUMERIC = "numeric"
    QUALITATIVE = "qualitative"
    BOUNDED_INEQUALITY = "bounded_inequality"
    RANGE = "range"
    TEXT = "text"


class NormalizationStatus(Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    REQUIRES_REVIEW = "requires_review"


class VerificationStatus(Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ImportRunStatus(Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class PlatformMessageLevel(Enum):
    INFORMATIONAL = "informational"
    ATTENTION = "attention"
    CONSULT_CLINICIAN = "consult_clinician"
    # URGENT_REVIEW is explicitly excluded per Sprint 1.1 / Sprint 2 medical safety guidelines.


@dataclass(frozen=True)
class BiomarkerDefinition:
    """Immutable definition of a canonical biomarker in the registry."""

    canonical_code: str
    canonical_name: str
    category: BiomarkerCategory
    default_unit: str
    accepted_aliases: Tuple[str, ...]
    accepted_units: Tuple[str, ...]
    value_type: BiomarkerValueType
    interpretation_policy: str = "standard"
    active: bool = True
    registry_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.canonical_code or not self.canonical_code.strip():
            raise InvalidBiomarkerDefinitionError("canonical_code cannot be empty or whitespace.")

        normalized_code = self.canonical_code.strip().lower()
        if not re.match(r"^[a-z0-9_\-]+$", normalized_code):
            raise InvalidBiomarkerDefinitionError(
                f"canonical_code '{self.canonical_code}' must be a valid normalized slug (alphanumeric, underscores, hyphens)."
            )
        object.__setattr__(self, "canonical_code", normalized_code)

        if not self.canonical_name or not self.canonical_name.strip():
            raise InvalidBiomarkerDefinitionError("canonical_name cannot be empty.")
        object.__setattr__(self, "canonical_name", self.canonical_name.strip())

        # Normalize accepted aliases (trimmed, case-insensitive) and reject duplicates within definition
        seen_aliases = set()
        normalized_aliases = []
        for alias in self.accepted_aliases:
            cleaned = alias.strip()
            if not cleaned:
                continue
            lower_cleaned = cleaned.lower()
            if lower_cleaned in seen_aliases:
                raise InvalidBiomarkerDefinitionError(
                    f"Duplicate alias '{cleaned}' in definition for '{self.canonical_code}'."
                )
            seen_aliases.add(lower_cleaned)
            normalized_aliases.append(cleaned)

        object.__setattr__(self, "accepted_aliases", tuple(normalized_aliases))

        # Normalize accepted units
        normalized_units = [u.strip() for u in self.accepted_units if u.strip()]
        object.__setattr__(self, "accepted_units", tuple(normalized_units))


@dataclass(frozen=True)
class LaboratoryReferenceRange:
    """Immutable laboratory reference range extracted from a specific report."""

    low: Optional[float] = None
    high: Optional[float] = None
    text: Optional[str] = None
    unit: Optional[str] = None
    laboratory_provided: bool = True
    demographic_context: Optional[str] = None
    fasting_status: Optional[str] = None

    def __post_init__(self) -> None:
        has_low = self.low is not None
        has_high = self.high is not None
        has_text = bool(self.text and self.text.strip())

        if not (has_low or has_high or has_text):
            raise ValueError(
                "LaboratoryReferenceRange must provide at least one of: low, high, or text."
            )

        if has_low and has_high and self.low > self.high:
            raise ValueError(
                f"Reference range low ({self.low}) cannot be greater than high ({self.high})."
            )


@dataclass(frozen=True)
class LaboratoryObservation:
    """Immutable domain representation of an observed biomarker result."""

    observation_id: str
    report_id: str
    import_run_id: str
    report_row_index: int
    observation_source_fingerprint: str

    raw_name: str
    raw_value: str
    raw_unit: str

    canonical_code: Optional[str] = None
    normalization_status: NormalizationStatus = NormalizationStatus.UNRESOLVED
    requires_review: bool = True
    alias_match_confidence: Optional[float] = None

    value_type: BiomarkerValueType = BiomarkerValueType.NUMERIC
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    qualitative_value: Optional[str] = None
    inequality_operator: Optional[str] = None
    range_low: Optional[float] = None
    range_high: Optional[float] = None

    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None

    laboratory_reference_range: Optional[LaboratoryReferenceRange] = None
    laboratory_flag: Optional[str] = None
    laboratory_provided_critical_flag: Optional[str] = None

    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reported_at: Optional[datetime] = None
    laboratory_name: Optional[str] = None
    source_type: str = "pdf_text"
    source_document_hash: Optional[str] = None

    name_confidence: float = 1.0
    value_confidence: float = 1.0
    unit_confidence: float = 1.0
    reference_confidence: float = 1.0
    extraction_confidence: float = 1.0
    overall_confidence: float = 1.0
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

    trend_status: Optional[str] = None
    training_context_signal: Optional[str] = None
    platform_message_level: PlatformMessageLevel = PlatformMessageLevel.INFORMATIONAL

    is_possible_duplicate: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id or not self.observation_id.strip():
            raise InvalidLaboratoryObservationError("observation_id cannot be empty.")
        if not self.report_id or not self.report_id.strip():
            raise InvalidLaboratoryObservationError("report_id cannot be empty.")
        if not self.import_run_id or not self.import_run_id.strip():
            raise InvalidLaboratoryObservationError("import_run_id cannot be empty.")

        # Enforcement of Normalization Invariants
        if self.normalization_status == NormalizationStatus.UNRESOLVED:
            if self.canonical_code is not None:
                raise InvalidLaboratoryObservationError(
                    "UNRESOLVED observation must have canonical_code = None."
                )
            if not self.requires_review:
                object.__setattr__(self, "requires_review", True)

        if self.normalization_status == NormalizationStatus.RESOLVED:
            if self.canonical_code is None or not self.canonical_code.strip():
                raise InvalidLaboratoryObservationError(
                    "RESOLVED observation must have a non-empty canonical_code."
                )


@dataclass(frozen=True)
class LaboratoryReport:
    """Immutable lab report metadata header."""

    report_id: str
    collected_at: datetime
    source_type: str
    source_document_hash: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reported_at: Optional[datetime] = None
    laboratory_name: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.report_id or not self.report_id.strip():
            raise ValueError("report_id cannot be empty.")
        if not self.source_document_hash or not self.source_document_hash.strip():
            raise ValueError("source_document_hash cannot be empty.")


@dataclass(frozen=True)
class LaboratoryImportRun:
    """
    Immutable ingestion run model for full provenance tracking.
    
    INVARIANT DOCUMENTATION (ADR-012):
    For any single report_id, at most ONE active LaboratoryImportRun (active == True)
    may exist. This invariant is enforced atomically across instances by the repository layer
    (deactivate previous active run, activate new run in a single transaction), not by individual dataclasses.
    """

    import_run_id: str
    report_id: str
    parser_version: str
    extractor_version: str
    registry_version: str
    unit_rules_version: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ImportRunStatus = ImportRunStatus.IN_PROGRESS
    active: bool = True
    warnings: Tuple[str, ...] = ()
    observations: Tuple[LaboratoryObservation, ...] = ()

    def __post_init__(self) -> None:
        if not self.import_run_id or not self.import_run_id.strip():
            raise InvalidImportRunError("import_run_id cannot be empty.")
        if not self.report_id or not self.report_id.strip():
            raise InvalidImportRunError("report_id cannot be empty.")

        if self.status == ImportRunStatus.COMPLETED and self.completed_at is None:
            raise InvalidImportRunError("completed_at is required when status is COMPLETED.")

        for obs in self.observations:
            if obs.report_id != self.report_id:
                raise InvalidImportRunError(
                    f"Observation {obs.observation_id} report_id '{obs.report_id}' does not match import run report_id '{self.report_id}'."
                )
            if obs.import_run_id != self.import_run_id:
                raise InvalidImportRunError(
                    f"Observation {obs.observation_id} import_run_id '{obs.import_run_id}' does not match import run id '{self.import_run_id}'."
                )


def calculate_observation_fingerprint(
    source_document_hash: str,
    report_id: str,
    import_run_id: str,
    report_row_index: int,
    raw_name: str,
    raw_value: str,
    raw_unit: str,
    collected_at: datetime,
) -> str:
    """
    Calculates a deterministic SHA-256 fingerprint for a laboratory observation.
    Uses explicit UTF-8 encoding and does NOT depend on file names or log raw data.
    """
    iso_date = collected_at.isoformat() if isinstance(collected_at, datetime) else str(collected_at)
    components = [
        str(source_document_hash).strip(),
        str(report_id).strip(),
        str(import_run_id).strip(),
        str(report_row_index),
        str(raw_name).strip(),
        str(raw_value).strip(),
        str(raw_unit).strip(),
        str(iso_date).strip(),
    ]
    payload = "|".join(components).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_laboratory_observation(
    observation_id: str,
    report_id: str,
    import_run_id: str,
    report_row_index: int,
    raw_name: str,
    raw_value: str,
    raw_unit: str,
    source_document_hash: str,
    collected_at: datetime,
    parsed_value: Any,
    biomarker_match: Any,
    unit_result: Optional[Any] = None,
    confidence_components: Optional[Any] = None,
    laboratory_reference_range: Optional[LaboratoryReferenceRange] = None,
    laboratory_flag: Optional[str] = None,
    laboratory_provided_critical_flag: Optional[str] = None,
    source_type: str = "pdf_text",
    laboratory_name: Optional[str] = None,
    is_possible_duplicate: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> LaboratoryObservation:
    """
    Factory function for instantiating a LaboratoryObservation from parsed values and registry matches.
    Keeps raw fields 100% intact and leaves platform_message_level neutral (INFORMATIONAL).
    """
    fingerprint = calculate_observation_fingerprint(
        source_document_hash=source_document_hash,
        report_id=report_id,
        import_run_id=import_run_id,
        report_row_index=report_row_index,
        raw_name=raw_name,
        raw_value=raw_value,
        raw_unit=raw_unit,
        collected_at=collected_at,
    )

    norm_val = unit_result.normalized_value if unit_result else None
    norm_unit = unit_result.normalized_unit if unit_result else None

    # Confidence components
    name_conf = confidence_components.name_confidence if confidence_components else 1.0
    val_conf = confidence_components.value_confidence if confidence_components else 1.0
    unit_conf = confidence_components.unit_confidence if confidence_components else 1.0
    ref_conf = confidence_components.reference_confidence if confidence_components else 1.0
    ext_conf = confidence_components.extraction_confidence if confidence_components else 1.0
    ver_stat = confidence_components.verification_status if confidence_components else VerificationStatus.UNVERIFIED

    return LaboratoryObservation(
        observation_id=observation_id,
        report_id=report_id,
        import_run_id=import_run_id,
        report_row_index=report_row_index,
        observation_source_fingerprint=fingerprint,
        raw_name=raw_name,
        raw_value=raw_value,
        raw_unit=raw_unit,
        canonical_code=biomarker_match.canonical_code,
        normalization_status=biomarker_match.normalization_status,
        requires_review=biomarker_match.requires_review,
        alias_match_confidence=biomarker_match.alias_match_confidence,
        value_type=parsed_value.value_type,
        numeric_value=parsed_value.numeric_value,
        text_value=parsed_value.text_value,
        qualitative_value=parsed_value.qualitative_value,
        inequality_operator=parsed_value.inequality_operator,
        range_low=parsed_value.range_low,
        range_high=parsed_value.range_high,
        normalized_value=norm_val,
        normalized_unit=norm_unit,
        laboratory_reference_range=laboratory_reference_range,
        laboratory_flag=laboratory_flag,
        laboratory_provided_critical_flag=laboratory_provided_critical_flag,
        collected_at=collected_at,
        laboratory_name=laboratory_name,
        source_type=source_type,
        source_document_hash=source_document_hash,
        name_confidence=name_conf,
        value_confidence=val_conf,
        unit_confidence=unit_conf,
        reference_confidence=ref_conf,
        extraction_confidence=ext_conf,
        overall_confidence=1.0,
        verification_status=ver_stat,
        platform_message_level=PlatformMessageLevel.INFORMATIONAL,  # Always neutral default
        is_possible_duplicate=is_possible_duplicate,
        metadata=metadata or {},
    )
