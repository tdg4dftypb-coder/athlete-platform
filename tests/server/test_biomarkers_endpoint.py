"""
HTTP Endpoint Tests for GET /api/v1/biomarkers, Shared Lifecycle & Dependency Injection.
"""

from datetime import datetime, timezone
import json
from unittest.mock import patch
import pytest

from biomarkers import (
    BiomarkersApplicationContext,
    LaboratoryIngestionRequest,
)
from biomarkers.contract_validator import validate_biomarkers_dashboard_payload
from server.app import create_dashboard_wsgi_app, dashboard_wsgi_app


def call_app(app_fn, path: str = "/api/v1/biomarkers", method: str = "GET") -> tuple[str, dict[str, str], bytes]:
    response_status = ""
    response_headers: dict[str, str] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        nonlocal response_status, response_headers
        response_status = status
        response_headers = {k.lower(): v for k, v in headers}

    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
    }
    body_chunks = app_fn(environ, start_response)
    body = b"".join(body_chunks)
    return response_status, response_headers, body


def test_get_biomarkers_endpoint_returns_200_and_valid_payload():
    status, headers, body = call_app(dashboard_wsgi_app, "/api/v1/biomarkers", "GET")

    assert status == "200 OK"
    assert "application/json" in headers.get("content-type", "")

    payload = json.loads(body.decode("utf-8"))
    assert payload["contract_version"] == "1.0"
    assert payload["metadata"]["status"] in ("ready", "partial", "unavailable")

    # Contract validation check
    errors = validate_biomarkers_dashboard_payload(payload)
    assert errors == []


def test_biomarkers_endpoint_cors_hardening():
    status, headers, body = call_app(dashboard_wsgi_app, "/api/v1/biomarkers", "GET")

    # Wildcard CORS Access-Control-Allow-Origin: * must NOT be present on hardened biomarkers endpoint
    assert "access-control-allow-origin" not in headers


def test_ingestion_then_endpoint_returns_data_from_shared_context():
    # 1. Create isolated BiomarkersApplicationContext
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    context = BiomarkersApplicationContext(clock=lambda: now)

    # 2. Ingest synthetic lab report into context.repository
    content = b"0 | Glukoza | 90 | mg/dL | 70-99"
    ingest_res = context.ingestion_service.ingest(LaboratoryIngestionRequest(content=content))
    assert ingest_res.report is not None

    # 3. Create WSGI app instance injected with this context
    app = create_dashboard_wsgi_app(biomarkers_context=context)

    # 4. Perform GET request
    status, headers, body = call_app(app, "/api/v1/biomarkers", "GET")
    assert status == "200 OK"

    payload = json.loads(body.decode("utf-8"))
    assert payload["summary"]["total_reports"] == 1
    assert payload["summary"]["total_observations"] == 1
    assert payload["metadata"]["status"] in ("ready", "partial")

    # Privacy assertions
    body_str = body.decode("utf-8")
    assert "source_document_hash" not in body_str
    assert "original_filename" not in body_str


def test_multiple_get_requests_preserve_repository_state():
    context = BiomarkersApplicationContext()
    content = b"0 | Glukoza | 90 | mg/dL | 70-99"
    context.ingestion_service.ingest(LaboratoryIngestionRequest(content=content))

    app = create_dashboard_wsgi_app(biomarkers_context=context)

    # First request
    status1, _, body1 = call_app(app, "/api/v1/biomarkers", "GET")
    p1 = json.loads(body1.decode("utf-8"))

    # Second request
    status2, _, body2 = call_app(app, "/api/v1/biomarkers", "GET")
    p2 = json.loads(body2.decode("utf-8"))

    assert status1 == "200 OK"
    assert status2 == "200 OK"
    assert p1["summary"]["total_reports"] == 1
    assert p2["summary"]["total_reports"] == 1  # State preserved, not reset!


def test_biomarkers_endpoint_post_method_returns_405():
    status, headers, body = call_app(dashboard_wsgi_app, "/api/v1/biomarkers", "POST")
    assert status == "405 Method Not Allowed"
    payload = json.loads(body.decode("utf-8"))
    assert "error" in payload


def test_biomarkers_endpoint_exception_returns_controlled_500():
    with patch("server.app.build_biomarkers_dashboard_use_case", side_effect=RuntimeError("Internal composition failure")):
        status, headers, body = call_app(dashboard_wsgi_app, "/api/v1/biomarkers", "GET")

        assert status == "500 Internal Server Error"
        assert "application/json" in headers.get("content-type", "")

        payload = json.loads(body.decode("utf-8"))
        assert "error" in payload
        assert "Internal composition failure" not in payload["error"]  # Zero trace leakage!
