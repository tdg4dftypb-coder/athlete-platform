from typing import Any, Dict
from biomarkers.intelligence.models import BiomarkerInsight
from biomarkers.trends.serialization import BiomarkerTrendSerializer


class BiomarkerInsightSerializer:
    """
    Serializer responsible for converting BiomarkerInsight objects into plain dictionaries.
    Leverages BiomarkerTrendSerializer for the nested trend field.
    """

    @staticmethod
    def serialize(insight: BiomarkerInsight) -> Dict[str, Any]:
        return {
            "canonical_code": insight.canonical_code,
            "interpretation": insight.interpretation.name.lower(),
            "confidence": insight.confidence.name.lower(),
            "summary": insight.summary,
            "reasoning": insight.reasoning,
            "trend": BiomarkerTrendSerializer.serialize(insight.trend),
        }
