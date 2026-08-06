from __future__ import annotations

from enum import Enum
from typing import Any

from morning_briefing.domain import (
    MorningBriefing,
    MorningSection,
    MorningMetric,
    MorningRecommendation,
)


def _serialize_value(v: Any) -> Any:
    """Serialize a single value: enums → lowercase str, None → None, others pass through."""
    if v is None:
        return None
    if isinstance(v, Enum):
        return v.value
    return v


class MorningBriefingSerializer:
    """Stateless serializer converting MorningBriefing to a JSON-safe dict.

    Does not perform any business logic, generate recommendations,
    or access any infrastructure layer.
    """

    def serialize(self, briefing: MorningBriefing) -> dict[str, object]:
        return {
            "generated_at": briefing.generated_at.isoformat(),
            "status": briefing.status.value,
            "sections": [self._serialize_section(s) for s in briefing.sections],
        }

    def _serialize_section(self, section: MorningSection) -> dict[str, object]:
        return {
            "title": section.title,
            "summary": section.summary,
            "metrics": [self._serialize_metric(m) for m in section.metrics],
            "recommendations": [self._serialize_recommendation(r) for r in section.recommendations],
        }

    def _serialize_metric(self, metric: MorningMetric) -> dict[str, object]:
        return {
            "title": metric.title,
            "value": _serialize_value(metric.value),
            "unit": _serialize_value(metric.unit),
            "status": _serialize_value(metric.status),
        }

    def _serialize_recommendation(self, rec: MorningRecommendation) -> dict[str, object]:
        return {
            "title": rec.title,
            "description": rec.description,
            "priority": rec.priority.value,
        }
