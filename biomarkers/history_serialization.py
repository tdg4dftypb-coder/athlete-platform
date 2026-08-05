"""
JSON-native Serializer for Biomarker History Public Contract (HistoryPayloadV1).

Sprint 7E — Biomarker History HTTP API.

Privacy boundary — pola WYKLUCZONE z payloadu publicznego:
  - observation_id, report_id, import_run_id
  - source_document_hash, filename, original_filename, raw_value
  - żadne wewnętrzne metadane repozytorium
"""

from datetime import datetime
import math
from typing import Any, Dict, List, Optional

from biomarkers.history import BiomarkerHistory, BiomarkerMeasurement


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Converts aware datetime to ISO 8601 string, returns None if absent."""
    if dt is None:
        return None
    return dt.isoformat()


def _sanitize_float(val: Optional[float]) -> Optional[float]:
    """Ensures floats are JSON-serializable (non-NaN / non-Infinity)."""
    if val is None:
        return None
    if not math.isfinite(val):
        return None
    return val


# ---------------------------------------------------------------------------
# Public serializer
# ---------------------------------------------------------------------------


class BiomarkerHistorySerializer:
    """
    Serializes BiomarkerHistory into a JSON-native dictionary payload
    adhering strictly to HistoryPayloadV1 public contract.

    Privacy invariant: no repository-internal fields are ever emitted.
    Ordering invariant: measurement order from BiomarkerHistoryBuilder is preserved
    without re-sorting.
    """

    CONTRACT_VERSION = "1.0"

    @staticmethod
    def serialize_measurement(measurement: BiomarkerMeasurement) -> Dict[str, Any]:
        """
        Maps BiomarkerMeasurement → HistoryMeasurementPayload.

        Exposed fields only:
          collected_at, numeric_value, qualitative_value,
          laboratory_flag, verification_status
        """
        return {
            "collected_at": _serialize_datetime(measurement.collected_at),
            "numeric_value": _sanitize_float(measurement.numeric_value),
            "qualitative_value": measurement.qualitative_value,
            "laboratory_flag": measurement.laboratory_flag,
            "verification_status": measurement.verification_status.value,
        }

    @staticmethod
    def serialize(history: BiomarkerHistory) -> Dict[str, Any]:
        """
        Maps BiomarkerHistory → HistoryPayloadV1.

        Preserves measurement ordering exactly as delivered by BiomarkerHistoryBuilder
        (oldest → newest). Does NOT perform additional sorting.

        Privacy-audited: raw_value, filename, original_filename,
        source_document_hash, report_id, observation_id, import_run_id
        are never present in the returned dictionary.
        """
        measurements: List[Dict[str, Any]] = [
            BiomarkerHistorySerializer.serialize_measurement(m)
            for m in history.measurements
        ]

        return {
            "contract_version": BiomarkerHistorySerializer.CONTRACT_VERSION,
            "canonical_code": history.canonical_code,
            "display_name": history.display_name,
            "preferred_unit": history.preferred_unit,
            "measurements": measurements,
        }
