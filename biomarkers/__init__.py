"""
Biomarkers & Laboratory Intelligence Domain Package.
"""

from biomarkers.confidence import (
    ConfidenceAssessment,
    ConfidenceComponents,
    evaluate_confidence_eligibility,
)
from biomarkers.errors import (
    BiomarkersError,
    DuplicateAliasError,
    DuplicateCanonicalCodeError,
    DuplicateUnitConversionRuleError,
    InvalidBiomarkerDefinitionError,
    InvalidConfidenceComponentError,
    InvalidImportRunError,
    InvalidLaboratoryObservationError,
    InvalidLaboratoryValueError,
    InvalidUnitConversionRuleError,
    UnitConversionNotAvailableError,
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
    # Enums
    "BiomarkerCategory",
    "BiomarkerValueType",
    "NormalizationStatus",
    "VerificationStatus",
    "ImportRunStatus",
    "PlatformMessageLevel",
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
]
