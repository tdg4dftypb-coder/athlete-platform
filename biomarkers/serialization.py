"""
JSON-native Serializer for BiomarkersDashboardPayloadV1 Public Contract.
"""

from datetime import datetime
from enum import Enum
import math
from typing import Any, Dict, List, Optional

from biomarkers.dashboard import (
    BiomarkerCategorySummary,
    BiomarkerSummary,
    BiomarkersDashboard,
    UnresolvedBiomarkerItem,
)


def _serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Helper to convert aware datetime objects to ISO 8601 strings."""
    if dt is None:
        return None
    return dt.isoformat()


def _sanitize_float(val: Optional[float]) -> Optional[float]:
    """Ensures floats are JSON-serializable and non-NaN/non-Infinity."""
    if val is None:
        return None
    if not math.isfinite(val):
        return None
    return val


class BiomarkersDashboardSerializer:
    """
    Serializes BiomarkersDashboard instances into a JSON-native dictionary payload
    adhering strictly to BiomarkersDashboardPayloadV1 public contract.
    """

    @staticmethod
    def serialize(dashboard: BiomarkersDashboard) -> Dict[str, Any]:
        """
        Serializes BiomarkersDashboard into JSON-native dictionary.
        Enforces contract_version="1.0", ISO 8601 timestamps, enum values,
        and privacy boundaries (no document hashes, no file names, no raw_value in unresolved items).
        """
        metadata_dict = {
            "status": dashboard.metadata.status.value,
            "completeness_score": _sanitize_float(dashboard.metadata.completeness_score),
            "limitations": list(dashboard.metadata.limitations),
            "evidence": list(dashboard.metadata.evidence),
            "generated_at": _serialize_datetime(dashboard.metadata.generated_at),
            "data_as_of": _serialize_datetime(dashboard.metadata.data_as_of),
        }

        summary_dict = {
            "total_reports": dashboard.total_reports,
            "active_reports": dashboard.active_reports,
            "total_observations": dashboard.total_observations,
            "verified_observations": dashboard.verified_observations,
            "unresolved_observations": dashboard.unresolved_observations,
            "possible_duplicates": dashboard.possible_duplicates,
            "latest_collection_date": dashboard.latest_collection_date,
        }

        categories_list: List[Dict[str, Any]] = []
        for cat in dashboard.categories:
            biomarkers_list: List[Dict[str, Any]] = []
            for b in cat.biomarkers:
                biomarkers_list.append(
                    {
                        "canonical_code": b.canonical_code,
                        "canonical_name": b.canonical_name,
                        "category": b.category.value,
                        "latest_observation_id": b.latest_observation_id,
                        "latest_value": _sanitize_float(b.latest_value),
                        "latest_text_value": b.latest_text_value,
                        "inequality_operator": b.inequality_operator,
                        "normalized_unit": b.normalized_unit,
                        "raw_unit": b.raw_unit,
                        "laboratory_reference_text": b.laboratory_reference_text,
                        "laboratory_flag": b.laboratory_flag,
                        "laboratory_provided_critical_flag": b.laboratory_provided_critical_flag,
                        "collected_at": _serialize_datetime(b.collected_at),
                        "trend_direction": b.trend_direction,
                        "trend_available": b.trend_available,
                        "observation_count": b.observation_count,
                        "verification_status": b.verification_status.value,
                        "data_quality": b.data_quality,
                        "limitations": list(b.limitations),
                    }
                )

            categories_list.append(
                {
                    "category": cat.category.value,
                    "display_name": cat.display_name,
                    "attention_count": cat.attention_count,
                    "unresolved_count": cat.unresolved_count,
                    "limitations": list(cat.limitations),
                    "biomarkers": biomarkers_list,
                }
            )

        unresolved_list: List[Dict[str, Any]] = []
        for u in dashboard.unresolved_items:
            unresolved_list.append(
                {
                    "observation_id": u.observation_id,
                    "raw_name": u.raw_name,
                    "raw_unit": u.raw_unit,
                    "collected_at": _serialize_datetime(u.collected_at),
                    "requires_review": u.requires_review,
                    "normalization_status": u.normalization_status.value,
                    "safe_reason": u.safe_reason,
                    # STRICT PRIVACY RULE: raw_value is omitted in public unresolved summary!
                }
            )

        return {
            "contract_version": "1.0",
            "as_of": _serialize_datetime(dashboard.metadata.generated_at),
            "metadata": metadata_dict,
            "summary": summary_dict,
            "categories": categories_list,
            "unresolved_items": unresolved_list,
            "data_quality": dashboard.data_quality_summary,
        }
