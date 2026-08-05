"""
Unit tests for BiomarkersDashboardPayloadV1 Contract Validator.
"""

from datetime import datetime, timezone
from biomarkers.composition import build_biomarkers_dashboard_use_case
from biomarkers.contract_validator import validate_biomarkers_dashboard_payload


def test_validator_passes_for_valid_composition_payload():
    payload = build_biomarkers_dashboard_use_case(clock=lambda: datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc))
    errors = validate_biomarkers_dashboard_payload(payload)
    assert errors == []


def test_validator_catches_invalid_contract_version():
    payload = {
        "contract_version": "2.0",
        "as_of": "2026-08-05T12:00:00Z",
        "metadata": {"status": "unavailable", "completeness_score": 0.0},
        "summary": {
            "total_reports": 0,
            "active_reports": 0,
            "total_observations": 0,
            "verified_observations": 0,
            "unresolved_observations": 0,
            "possible_duplicates": 0,
        },
        "categories": [],
        "unresolved_items": [],
        "data_quality": {},
    }
    errors = validate_biomarkers_dashboard_payload(payload)
    assert any("contract_version" in e for e in errors)


def test_validator_catches_privacy_violation_in_unresolved_items():
    payload = {
        "contract_version": "1.0",
        "as_of": "2026-08-05T12:00:00Z",
        "metadata": {"status": "partial", "completeness_score": 0.5},
        "summary": {
            "total_reports": 1,
            "active_reports": 1,
            "total_observations": 1,
            "verified_observations": 0,
            "unresolved_observations": 1,
            "possible_duplicates": 0,
        },
        "categories": [],
        "unresolved_items": [
            {
                "observation_id": "obs-1",
                "raw_name": "Glukoza",
                "raw_value": "90",  # Privacy violation!
                "raw_unit": "mg/dL",
                "collected_at": "2026-08-01T08:00:00Z",
                "requires_review": True,
                "normalization_status": "unresolved",
                "safe_reason": "test",
            }
        ],
        "data_quality": {},
    }
    errors = validate_biomarkers_dashboard_payload(payload)
    assert any("raw_value" in e for e in errors)
