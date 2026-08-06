from dataclasses import replace
from biomarkers.trends.models import BiomarkerTrend, TrendDirection, TrendStrength


class TrendClassifier:
    """
    Classifier responsible for interpreting trend direction and strength from mathematical values.
    """

    @staticmethod
    def classify(trend: BiomarkerTrend) -> BiomarkerTrend:
        if trend.relative_change is None or trend.observations < 2:
            return replace(
                trend,
                direction=TrendDirection.INSUFFICIENT_DATA,
                strength=TrendStrength.NONE,
            )

        rel = trend.relative_change
        abs_rel = abs(rel)

        # Classify direction
        if rel > 5.0:
            direction = TrendDirection.INCREASING
        elif rel < -5.0:
            direction = TrendDirection.DECREASING
        else:
            direction = TrendDirection.STABLE

        # Classify strength
        if abs_rel <= 5.0:
            strength = TrendStrength.NONE
        elif abs_rel <= 15.0:
            strength = TrendStrength.WEAK
        elif abs_rel <= 30.0:
            strength = TrendStrength.MODERATE
        else:
            strength = TrendStrength.STRONG

        return replace(trend, direction=direction, strength=strength)
