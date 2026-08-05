"""
Confidence Components and Eligibility Assessment Engine.
"""

from dataclasses import dataclass
from typing import Tuple

from biomarkers.errors import InvalidConfidenceComponentError
from biomarkers.models import (
    LaboratoryObservation,
    NormalizationStatus,
    VerificationStatus,
)


@dataclass(frozen=True)
class ConfidenceComponents:
    """
    Immutable representation of individual confidence components.
    Does NOT calculate an automatic overall_confidence weight formula in the model.
    Does NOT enforce hardcoded cutoffs (0.70 / 0.90) as permanent domain rules.
    """

    name_confidence: float = 1.0
    value_confidence: float = 1.0
    unit_confidence: float = 1.0
    reference_confidence: float = 1.0
    extraction_confidence: float = 1.0
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

    def __post_init__(self) -> None:
        scores = {
            "name_confidence": self.name_confidence,
            "value_confidence": self.value_confidence,
            "unit_confidence": self.unit_confidence,
            "reference_confidence": self.reference_confidence,
            "extraction_confidence": self.extraction_confidence,
        }
        for field_name, score in scores.items():
            if score is None or not (0.0 <= score <= 1.0):
                raise InvalidConfidenceComponentError(
                    f"{field_name} must be a float between 0.0 and 1.0 (got {score})."
                )


@dataclass(frozen=True)
class ConfidenceAssessment:
    """Immutable result of evaluating observation eligibility for trends and AI Coach."""

    components: ConfidenceComponents
    eligible_for_trends: bool
    eligible_for_ai_coach: bool
    reasons: Tuple[str, ...]


def evaluate_confidence_eligibility(obs: LaboratoryObservation) -> ConfidenceAssessment:
    """
    Evaluates conservative eligibility for trend plotting and AI Coach decision inputs.
    
    Trends Eligibility Policy:
    - Normalization status MUST be RESOLVED.
    - Parsed value MUST be valid (numeric, inequality, qualitative, or text).
    - Verification status MUST NOT be REJECTED.
    
    AI Coach Eligibility Policy:
    - MUST meet all Trends eligibility criteria.
    - Verification status MUST be explicitly VERIFIED by user.
    - MUST NOT be flagged as is_possible_duplicate.
    - MUST NOT contain unverified or unresolved biomarker data.
    """
    reasons = []

    components = ConfidenceComponents(
        name_confidence=obs.name_confidence,
        value_confidence=obs.value_confidence,
        unit_confidence=obs.unit_confidence,
        reference_confidence=obs.reference_confidence,
        extraction_confidence=obs.extraction_confidence,
        verification_status=obs.verification_status,
    )

    # 1. Trends Eligibility Check
    is_resolved = obs.normalization_status == NormalizationStatus.RESOLVED
    if not is_resolved:
        reasons.append("Unresolved biomarker code (normalization_status != RESOLVED).")

    has_parsed_value = (
        obs.numeric_value is not None
        or obs.inequality_operator is not None
        or obs.qualitative_value is not None
        or obs.text_value is not None
    )
    if not has_parsed_value:
        reasons.append("Missing valid parsed laboratory value.")

    not_rejected = obs.verification_status != VerificationStatus.REJECTED
    if not not_rejected:
        reasons.append("Observation verification status is REJECTED.")

    eligible_for_trends = is_resolved and has_parsed_value and not_rejected

    # 2. AI Coach Eligibility Check
    is_verified = obs.verification_status == VerificationStatus.VERIFIED
    if not is_verified:
        reasons.append("Observation is UNVERIFIED by user.")

    not_duplicate = not obs.is_possible_duplicate
    if not not_duplicate:
        reasons.append("Observation flagged as is_possible_duplicate.")

    eligible_for_ai_coach = eligible_for_trends and is_verified and not_duplicate

    return ConfidenceAssessment(
        components=components,
        eligible_for_trends=eligible_for_trends,
        eligible_for_ai_coach=eligible_for_ai_coach,
        reasons=tuple(reasons),
    )
