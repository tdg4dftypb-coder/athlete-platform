"""
HTTP Endpoint Tests for GET /api/v1/biomarkers.
"""

import json
from unittest.mock import patch
import pytest

from biomarkers.contract_validator import validate_biomarkers_dashboard_payload
from server.app import dashboard_wsgi_app


def call_app(path: str = "/api/v1/biomarkers", method: str = "GET") -> tuple[str, dict[str, str], bytes]:
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
    body_chunks = dashboard_wsgi_app(environ, start_response)
    body = b"".join(body_chunks)
    return response_status, response_headers, body


def test_get_biomarkers_endpoint_returns_200_and_valid_payload():
    status, headers, body = call_app("/api/v1/biomarkers", "GET")

    assert status == "200 OK"
    assert "application/json" in headers.get("content-type", "")

    payload = json.loads(body.decode("utf-8"))
    assert payload["contract_version"] == "1.0"
    assert payload["metadata"]["status"] in ("ready", "partial", "unavailable")

    # Contract validation check
    errors = validate_biomarkers_dashboard_payload(payload)
    assert errors == []


def test_biomarkers_endpoint_privacy_assertions():
    status, headers, body = call_app("/api/v1/biomarkers", "GET")
    body_str = body.decode("utf-8")

    assert "source_document_hash" not in body_str
    assert "original_filename" not in body_str


def test_biomarkers_endpoint_post_method_returns_405():
    status, headers, body = call_app("/api/v1/biomarkers", "POST")
    assert status == "405 Method Not Allowed"
    payload = json.loads(body.decode("utf-8"))
    assert "error" in payload


def test_biomarkers_endpoint_exception_returns_controlled_500():
    with patch("server.app.build_biomarkers_dashboard_use_case", side_effect=RuntimeError("Internal composition failure")):
        status, headers, body = call_app("/api/v1/biomarkers", "GET")

        assert status == "500 Internal Server Error"
        assert "application/json" in headers.get("content-type", "")

        payload = json.loads(body.decode("utf-8"))
        assert "error" in payload
        assert "Internal composition failure" not in payload["error"]  # Zero trace leakage!
