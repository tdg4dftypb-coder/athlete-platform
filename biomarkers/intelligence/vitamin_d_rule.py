from biomarkers.trends.models import BiomarkerTrend, TrendDirection
from biomarkers.intelligence.models import (
    BiomarkerInsight,
    Interpretation,
    ConfidenceLevel,
)
from biomarkers.intelligence.rules import BiomarkerInsightRule


class VitaminDRule(BiomarkerInsightRule):
    """
    Interpretation rule specific to Vitamin D biomarker.
    Stable and increasing trends are both clinically positive; decreasing is negative.
    """

    def supports(self, canonical_code: str) -> bool:
        return canonical_code == "vitamin_d_25_oh"

    def evaluate(self, trend: BiomarkerTrend) -> BiomarkerInsight:
        direction = trend.direction

        if direction == TrendDirection.INCREASING:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.POSITIVE,
                confidence=ConfidenceLevel.HIGH,
                summary="Vitamin D is improving.",
                reasoning="Vitamin D shows an increasing trend.",
                trend=trend,
            )
        elif direction == TrendDirection.STABLE:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.POSITIVE,
                confidence=ConfidenceLevel.HIGH,
                summary="Vitamin D remains stable.",
                reasoning="Vitamin D remains at a stable level.",
                trend=trend,
            )
        elif direction == TrendDirection.DECREASING:
            return BiomarkerInsight(
                canonical_code=trend.canonical_code,
                interpretation=Interpretation.NEGATIVE,
                confidence=ConfidenceLevel.HIGH,
                summary="Vitamin D is decreasing.",
                reasoning="Vitamin D shows a decreasing trend.",
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
