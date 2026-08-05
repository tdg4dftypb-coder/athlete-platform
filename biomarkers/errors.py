"""
Domain exceptions for Biomarkers & Laboratory Intelligence.
"""


class BiomarkersError(Exception):
    """Base exception for all biomarkers domain errors."""

    pass


class InvalidBiomarkerDefinitionError(BiomarkersError):
    """Raised when a BiomarkerDefinition fails validation or invariant checks."""

    pass


class DuplicateCanonicalCodeError(BiomarkersError):
    """Raised when attempting to register a canonical_code that already exists in the registry."""

    pass


class DuplicateAliasError(BiomarkersError):
    """Raised when an alias collides with an existing registered alias or canonical code."""

    pass


class InvalidLaboratoryObservationError(BiomarkersError):
    """Raised when a LaboratoryObservation fails validation or invariant checks."""

    pass


class InvalidImportRunError(BiomarkersError):
    """Raised when a LaboratoryImportRun fails validation or invariant checks."""

    pass


class InvalidUnitConversionRuleError(BiomarkersError):
    """Raised when a UnitConversionRule fails validation or invariant checks."""

    pass


class DuplicateUnitConversionRuleError(BiomarkersError):
    """Raised when attempting to register a duplicate UnitConversionRule."""

    pass


class UnitConversionNotAvailableError(BiomarkersError):
    """Raised when unit conversion is requested but no conversion rule exists."""

    pass


class InvalidLaboratoryValueError(BiomarkersError):
    """Raised when parsing a laboratory raw value fails or input is invalid."""

    pass


class InvalidConfidenceComponentError(BiomarkersError):
    """Raised when confidence component values fail validation."""

    pass


# Privacy-safe domain errors (exception messages MUST NOT leak raw health values or PII)
class EmptySourceDocumentError(BiomarkersError):
    """Raised when an empty source document content is provided for ingestion."""

    pass


class DuplicateSourceDocumentError(BiomarkersError):
    """Raised when an identical source document hash already exists."""

    pass


class LaboratoryIngestionError(BiomarkersError):
    """Raised when laboratory ingestion processing fails."""

    pass


class ReportNotFoundError(BiomarkersError):
    """Raised when a requested laboratory report cannot be found."""

    pass


class ImportRunActivationError(BiomarkersError):
    """Raised when activating a LaboratoryImportRun fails."""

    pass


class LaboratoryDeletionError(BiomarkersError):
    """Raised when deleting a laboratory report or document fails."""

    pass
