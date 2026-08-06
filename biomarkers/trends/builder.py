from biomarkers.history import BiomarkerHistory
from biomarkers.trends.models import (
    BiomarkerTrend,
    TrendDirection,
    TrendStrength,
    TrendWindow,
)


class BiomarkerTrendBuilder:
    """
    Builder responsible for calculating mathematical trend properties from BiomarkerHistory.
    """

    @staticmethod
    def build_trend(history: BiomarkerHistory) -> BiomarkerTrend:
        numeric_values = [
            m.numeric_value
            for m in history.measurements
            if m.numeric_value is not None
        ]

        direction = TrendDirection.INSUFFICIENT_DATA
        strength = TrendStrength.NONE
        window = TrendWindow.ALL_TIME

        if not numeric_values:
            return BiomarkerTrend(
                canonical_code=history.canonical_code,
                first_value=None,
                latest_value=None,
                absolute_change=None,
                relative_change=None,
                direction=direction,
                strength=strength,
                window=window,
                observations=len(history.measurements),
            )

        if len(numeric_values) == 1:
            val = numeric_values[0]
            return BiomarkerTrend(
                canonical_code=history.canonical_code,
                first_value=val,
                latest_value=val,
                absolute_change=0.0,
                relative_change=0.0,
                direction=direction,
                strength=strength,
                window=window,
                observations=1,
            )

        first_value = numeric_values[0]
        latest_value = numeric_values[-1]
        absolute_change = latest_value - first_value

        if first_value == 0.0:
            relative_change = None
        else:
            relative_change = ((latest_value - first_value) / first_value) * 100

        return BiomarkerTrend(
            canonical_code=history.canonical_code,
            first_value=first_value,
            latest_value=latest_value,
            absolute_change=absolute_change,
            relative_change=relative_change,
            direction=direction,
            strength=strength,
            window=window,
            observations=len(numeric_values),
        )
