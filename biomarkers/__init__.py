"""
Biomarkers & Laboratory Intelligence Domain Package.
"""

from biomarkers.composition import (
    BiomarkersApplicationContext,
    build_biomarkers_dashboard_use_case,
    get_default_biomarkers_context,
)
from biomarkers.confidence import (
    ConfidenceAssessment,
    ConfidenceComponents,
    evaluate_confidence_eligibility,
)
from biomarkers.dashboard import (
    CATEGORY_DISPLAY_NAMES,
    BiomarkerCategorySummary,
    BiomarkersDashboard,
    BiomarkersDashboardBuilder,
    BiomarkersDashboardMetadata,
    BiomarkersDashboardStatus,
    BiomarkerSummary,
    UnresolvedBiomarkerItem,
)
from biomarkers.deletion import (
    DeletionMode,
    DeletionResult,
    InMemorySourceDocumentStore,
    LaboratoryDeletionService,
    SourceDocumentStore,
    TombstoneRecord,
)
from biomarkers.errors import (
    BiomarkersError,
    DuplicateAliasError,
    DuplicateCanonicalCodeError,
    DuplicateSourceDocumentError,
    DuplicateUnitConversionRuleError,
    EmptySourceDocumentError,
    ImportRunActivationError,
    InvalidBiomarkerDefinitionError,
    InvalidConfidenceComponentError,
    InvalidImportRunError,
    InvalidLaboratoryObservationError,
    InvalidLaboratoryValueError,
    InvalidUnitConversionRuleError,
    LaboratoryDeletionError,
    LaboratoryIngestionError,
    ReportNotFoundError,
    UnitConversionNotAvailableError,
)
from biomarkers.history import (
    BiomarkerHistory,
    BiomarkerHistoryBuilder,
    BiomarkerMeasurement,
)
from biomarkers.ingestion import (
    ExtractedDocument,
    LaboratoryDocumentExtractor,
    LaboratoryIngestionRequest,
    LaboratoryIngestionResult,
    LaboratoryIngestionService,
    LaboratoryResultParser,
    RawLaboratoryRow,
    SourceDocumentIdentity,
    SyntheticLaboratoryDocumentExtractor,
    SyntheticLaboratoryResultParser,
    calculate_source_document_hash,
)
from biomarkers.models import (
    BiomarkerCategory,
    BiomarkerDefinition,
    BiomarkerValueType,
    ImportRunStatus,
    LaboratoryImportRun,
    LaboratoryObservation,
    LaboratoryReferenceRange,
    LaboratoryReport,
    NormalizationStatus,
    PlatformMessageLevel,
    VerificationStatus,
    calculate_observation_fingerprint,
    create_laboratory_observation,
)
from biomarkers.registry import (
    BiomarkerMatch,
    BiomarkerRegistry,
    create_default_biomarker_registry,
)
from biomarkers.repository import (
    InMemoryLaboratoryRepository,
    LaboratoryRepository,
)
from biomarkers.serialization import BiomarkersDashboardSerializer
from biomarkers.units import (
    UnitAliasRegistry,
    UnitConversionRule,
    UnitNormalizationResult,
    UnitNormalizer,
    create_default_unit_normalizer,
)
from biomarkers.values import (
    ParsedLaboratoryValue,
    parse_laboratory_value,
)

__all__ = [
    # Errors
    "BiomarkersError",
    "InvalidBiomarkerDefinitionError",
    "DuplicateCanonicalCodeError",
    "DuplicateAliasError",
    "InvalidLaboratoryObservationError",
    "InvalidImportRunError",
    "InvalidUnitConversionRuleError",
    "DuplicateUnitConversionRuleError",
    "UnitConversionNotAvailableError",
    "InvalidLaboratoryValueError",
    "InvalidConfidenceComponentError",
    "EmptySourceDocumentError",
    "DuplicateSourceDocumentError",
    "LaboratoryIngestionError",
    "ReportNotFoundError",
    "ImportRunActivationError",
    "LaboratoryDeletionError",
    # Enums
    "BiomarkerCategory",
    "BiomarkerValueType",
    "NormalizationStatus",
    "VerificationStatus",
    "ImportRunStatus",
    "PlatformMessageLevel",
    "DeletionMode",
    "BiomarkersDashboardStatus",
    # Domain Models & Functions
    "BiomarkerDefinition",
    "LaboratoryReferenceRange",
    "LaboratoryObservation",
    "LaboratoryReport",
    "LaboratoryImportRun",
    "calculate_observation_fingerprint",
    "create_laboratory_observation",
    # Registry
    "BiomarkerMatch",
    "BiomarkerRegistry",
    "create_default_biomarker_registry",
    # Units
    "UnitConversionRule",
    "UnitAliasRegistry",
    "UnitNormalizationResult",
    "UnitNormalizer",
    "create_default_unit_normalizer",
    # Values
    "ParsedLaboratoryValue",
    "parse_laboratory_value",
    # Confidence
    "ConfidenceComponents",
    "ConfidenceAssessment",
    "evaluate_confidence_eligibility",
    # Ingestion
    "SourceDocumentIdentity",
    "calculate_source_document_hash",
    "RawLaboratoryRow",
    "ExtractedDocument",
    "LaboratoryDocumentExtractor",
    "LaboratoryResultParser",
    "SyntheticLaboratoryDocumentExtractor",
    "SyntheticLaboratoryResultParser",
    "LaboratoryIngestionRequest",
    "LaboratoryIngestionResult",
    "LaboratoryIngestionService",
    # Repository & Store
    "LaboratoryRepository",
    "InMemoryLaboratoryRepository",
    "SourceDocumentStore",
    "InMemorySourceDocumentStore",
    # Deletion
    "TombstoneRecord",
    "DeletionResult",
    "LaboratoryDeletionService",
    # Dashboard, Composition & Serialization
    "BiomarkersDashboardMetadata",
    "BiomarkerSummary",
    "BiomarkerCategorySummary",
    "UnresolvedBiomarkerItem",
    "BiomarkersDashboard",
    "BiomarkersDashboardBuilder",
    "BiomarkersDashboardSerializer",
    "BiomarkersApplicationContext",
    "get_default_biomarkers_context",
    "build_biomarkers_dashboard_use_case",
    "CATEGORY_DISPLAY_NAMES",
    # History
    "BiomarkerMeasurement",
    "BiomarkerHistory",
    "BiomarkerHistoryBuilder",
]
