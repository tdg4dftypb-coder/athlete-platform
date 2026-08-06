from biomarkers.trends.models import BiomarkerTrend, TrendDirection
from biomarkers.intelligence.models import (
    BiomarkerInsight,
    Interpretation,
    ConfidenceLevel,
)
from biomarkers.intelligence.rules import BiomarkerInsightRule


class FerritinRule(BiomarkerInsightRule):
    """
    Interpretation rule specific to Ferritin biomarker.
    """

    def supports(self, canonical_code: str) -> bool:
        return canonical_code == "ferritin"

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        direction = trend.direction

        if direction == TrendDirection.INCREASING:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.POSITIVE,
                confidence=ConfidenceLevel.HIGH,
                summary="Ferritin is improving.",
                reasoning="Ferritin shows an increasing trend.",
                trend=trend,
            )
        elif direction == TrendDirection.DECREASING:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.NEGATIVE,
                confidence=ConfidenceLevel.HIGH,
                summary="Ferritin is decreasing.",
                reasoning="Ferritin shows a decreasing trend.",
                trend=trend,
            )
        elif direction == TrendDirection.STABLE:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.NEUTRAL,
                confidence=ConfidenceLevel.HIGH,
                summary="Ferritin remains stable.",
                reasoning="Generic trend interpretation.",
                trend=trend,
            )
        else:
            # INSUFFICIENT_DATA
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.UNKNOWN,
                confidence=ConfidenceLevel.NONE,
                summary="Biomarker trend interpretation is unavailable.",
                reasoning="Generic trend interpretation.",
                trend=trend,
            )
        
