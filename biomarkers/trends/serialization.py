from typing import Any, Dict
from biomarkers.trends.models import BiomarkerTrend


class BiomarkerTrendSerializer:
    """
    Serializer responsible for converting BiomarkerTrend objects into plain dictionaries.
    """

    @staticmethod
    def serialize(trend: BiomarkerTrend) -> Dict[str, Any]:
        return {
            "canonical_code": trend.canonical_code,
            "first_value": trend.first_value,
            "latest_value": trend.latest_value,
            "absolute_change": trend.absolute_change,
            "relative_change": trend.relative_change,
            "direction": trend.direction.name.lower(),
            "strength": trend.strength.name.lower(),
            "window": trend.window.name.lower(),
            "observations": trend.observations,
        }
