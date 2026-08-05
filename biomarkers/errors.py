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
