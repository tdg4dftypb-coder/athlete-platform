import json
from unittest.mock import patch
import pytest

from server.app import dashboard_wsgi_app
from dashboard.serialization import DashboardSerializer


def call_app(path: str = "/api/v1/dashboard", method: str = "GET") -> tuple[str, dict[str, str], bytes]:
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


def test_get_dashboard_endpoint_returns_200_and_valid_contract():
    status, headers, body = call_app("/api/v1/dashboard", "GET")

    assert status == "200 OK"
    assert "application/json" in headers.get("content-type", "")

    payload = json.loads(body.decode("utf-8"))
    assert payload["contract_version"] == "1.0"

    restored = DashboardSerializer().deserialize(payload)
    assert restored.contract_version == "1.0"


def test_get_dashboard_endpoint_handles_use_case_failure_with_500():
    with patch("server.app.build_morning_coach_use_case", side_effect=RuntimeError("Database connection failed")):
        status, headers, body = call_app("/api/v1/dashboard", "GET")

        assert status == "500 Internal Server Error"
        assert "application/json" in headers.get("content-type", "")

        payload = json.loads(body.decode("utf-8"))
        assert "error" in payload
        assert "Database connection failed" not in payload["error"]  # no leaked trace details


def test_unknown_endpoint_returns_404():
    status, headers, body = call_app("/unknown", "GET")
    assert status == "404 Not Found"
