from abc import ABC, abstractmethod
from biomarkers.trends.models import BiomarkerTrend, TrendDirection
from biomarkers.intelligence.models import (
    BiomarkerInsight,
    Interpretation,
    ConfidenceLevel,
)


class BiomarkerInsightRule(ABC):
    """
    Abstract Base Class representing a single interpretation rule for a biomarker trend.
    """

    @abstractmethod
    def supports(self, canonical_code: str) -> bool:
        """Determines if the rule can process the given biomarker."""
        pass

    @abstractmethod
    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        """Evaluates the trend and produces a domain insight."""
        pass


class GenericIncreasingRule(BiomarkerInsightRule):
    def supports(self, canonical_code: str) -> bool:
        return True

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        return BiomarkerInsight(
            canonical_code=trend.canonical_code,
            interpretation=Interpretation.UNKNOWN,
            confidence=ConfidenceLevel.NONE,
            summary="Biomarker shows an increasing trend.",
            reasoning="Generic trend interpretation.",
            trend=trend,
        )


class GenericDecreasingRule(BiomarkerInsightRule):
    def supports(self, canonical_code: str) -> bool:
        return True

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        return BiomarkerInsight(
            canonical_code=trend.canonical_code,
            interpretation=Interpretation.UNKNOWN,
            confidence=ConfidenceLevel.NONE,
            summary="Biomarker shows a decreasing trend.",
            reasoning="Generic trend interpretation.",
            trend=trend,
        )


class GenericStableRule(BiomarkerInsightRule):
    def supports(self, canonical_code: str) -> bool:
        return True

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        return BiomarkerInsight(
            canonical_code=trend.canonical_code,
            interpretation=Interpretation.UNKNOWN,
            confidence=ConfidenceLevel.NONE,
            summary="Biomarker shows a stable trend.",
            reasoning="Generic trend interpretation.",
            trend=trend,
        )


class GenericUnknownRule(BiomarkerInsightRule):
    def supports(self, canonical_code: str) -> bool:
        return True

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        return BiomarkerInsight(
            canonical_code=trend.canonical_code,
            interpretation=Interpretation.UNKNOWN,
            confidence=ConfidenceLevel.NONE,
            summary="Biomarker trend interpretation is unavailable.",
            reasoning="Generic trend interpretation.",
            trend=trend,
        )
