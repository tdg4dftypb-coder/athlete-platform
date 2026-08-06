from biomarkers.trends.models import BiomarkerTrend, TrendDirection
from biomarkers.intelligence.models import (
    BiomarkerInsight,
    Interpretation,
    ConfidenceLevel,
)
from biomarkers.intelligence.rules import BiomarkerInsightRule


class CRPRule(BiomarkerInsightRule):
    """
    Interpretation rule specific to CRP (C-Reactive Protein) inflammatory biomarker.
    Opposite clinical polarity compared to general metrics (increase is negative).
    """

    def supports(self, canonical_code: str) -> bool:
        return canonical_code == "crp"

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        direction = trend.direction

        if direction == TrendDirection.INCREASING:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.NEGATIVE,
                confidence=ConfidenceLevel.HIGH,
                summary="CRP is increasing.",
                reasoning="An increasing CRP trend may indicate growing inflammation.",
                trend=trend,
            )
        elif direction == TrendDirection.DECREASING:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.POSITIVE,
                confidence=ConfidenceLevel.HIGH,
                summary="CRP is improving.",
                reasoning="CRP shows a decreasing trend.",
                trend=trend,
            )
        elif direction == TrendDirection.STABLE:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.NEUTRAL,
                confidence=ConfidenceLevel.HIGH,
                summary="CRP remains stable.",
                reasoning="CRP trend is stable.",
                trend=trend,
            )
        else:
            # INSUFFICIENT_DATA
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.UNKNOWN,
                confidence=ConfidenceLevel.NONE,
                summary="Not enough data.",
                reasoning="More measurements are required.",
                trend=trend,
            )
