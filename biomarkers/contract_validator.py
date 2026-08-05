"""
Backend Contract Validator for BiomarkersDashboardPayloadV1.
"""

from datetime import datetime
import math

from typing import Any, Dict, List


def validate_biomarkers_dashboard_payload(payload: Dict[str, Any]) -> List[str]:
    """
    Validates a serialized BiomarkersDashboardPayloadV1 dictionary against contract requirements.
    Returns a list of error strings (empty list if valid).
    """
    errors: List[str] = []

    if not isinstance(payload, dict):
        return ["Payload must be a dictionary."]

    # 1. Contract version
    if payload.get("contract_version") != "1.0":
        errors.append(f"Invalid contract_version: '{payload.get('contract_version')}', expected '1.0'.")

    # 2. Timestamps
    as_of = payload.get("as_of")
    if not isinstance(as_of, str):
        errors.append("Field 'as_of' must be an ISO string.")

    # 3. Metadata
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("Field 'metadata' must be a dictionary.")
    else:
        status = metadata.get("status")
        if status not in ("ready", "partial", "unavailable"):
            errors.append(f"Invalid metadata status: '{status}'.")

        comp = metadata.get("completeness_score")
        if not isinstance(comp, (int, float)) or not (0.0 <= comp <= 1.0):
            errors.append(f"Invalid completeness_score: '{comp}', must be float between 0.0 and 1.0.")

    # 4. Summary
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("Field 'summary' must be a dictionary.")
    else:
        int_fields = [
            "total_reports",
            "active_reports",
            "total_observations",
            "verified_observations",
            "unresolved_observations",
            "possible_duplicates",
        ]
        for field_name in int_fields:
            val = summary.get(field_name)
            if not isinstance(val, int) or val < 0:
                errors.append(f"Summary field '{field_name}' must be an integer >= 0.")

    # 5. Categories
    categories = payload.get("categories")
    if not isinstance(categories, list):
        errors.append("Field 'categories' must be a list.")

    # 6. Unresolved Items & Privacy Assertions
    unresolved_items = payload.get("unresolved_items")
    if not isinstance(unresolved_items, list):
        errors.append("Field 'unresolved_items' must be a list.")
    else:
        for idx, item in enumerate(unresolved_items):
            if not isinstance(item, dict):
                errors.append(f"Unresolved item at index {idx} must be a dictionary.")
            elif "raw_value" in item:
                errors.append(f"Privacy violation: 'raw_value' present in unresolved item at index {idx}.")

    # 7. Privacy Assertions on root payload keys
    payload_str = str(payload)
    if "source_document_hash" in payload_str:
        errors.append("Privacy violation: 'source_document_hash' leaked in payload.")
    if "original_filename" in payload_str:
        errors.append("Privacy violation: 'original_filename' leaked in payload.")

    # 8. NaN / Infinity Check
    def _check_finite(obj: Any, path: str = "") -> None:
        if isinstance(obj, float):
            if not math.isfinite(obj):
                errors.append(f"Non-finite float value found at path '{path}'.")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _check_finite(v, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _check_finite(v, f"{path}[{i}]")

    _check_finite(payload)

    return errors
