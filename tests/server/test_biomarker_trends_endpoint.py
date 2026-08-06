from datetime import datetime, timezone
import json
import pytest

from biomarkers import (
    BiomarkersApplicationContext,
    LaboratoryIngestionRequest,
)
from server.app import create_dashboard_wsgi_app


def call_app(
    app_fn,
    path: str,
    method: str = "GET",
) -> tuple[str, dict[str, str], bytes]:
    response_status = ""
    response_headers: dict[str, str] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        nonlocal response_status, response_headers
        response_status = status
        response_headers = {k.lower(): v for k, v in headers}

    environ = {"PATH_INFO": path, "REQUEST_METHOD": method}
    chunks = app_fn(environ, start_response)
    body = b"".join(chunks)
    return response_status, response_headers, body


def trends_path(canonical_code: str) -> str:
    return f"/api/v1/biomarkers/trends/{canonical_code}"


def _ingest_row(context: BiomarkersApplicationContext, row: str) -> None:
    content = row.encode("utf-8")
    res = context.ingestion_service.ingest(LaboratoryIngestionRequest(content=content))
    assert res.report is not None


class TestTrendsEndpoint:
    def test_unknown_canonical_code_returns_404(self) -> None:
        context = BiomarkersApplicationContext()
        app = create_dashboard_wsgi_app(biomarkers_context=context)

        status, _, body = call_app(app, trends_path("non_existent_code"))
        assert status == "404 Not Found"
        payload = json.loads(body.decode("utf-8"))
        assert "error" in payload

    def test_invalid_canonical_code_returns_400(self) -> None:
        context = BiomarkersApplicationContext()
        app = create_dashboard_wsgi_app(biomarkers_context=context)

        status, _, _ = call_app(app, trends_path("InvalidCode"))
        assert status == "400 Bad Request"

        status, _, _ = call_app(app, trends_path("code_with_spaces "))
        assert status == "400 Bad Request"

    def test_empty_history_for_valid_biomarker_returns_200(self) -> None:
        context = BiomarkersApplicationContext()
        app = create_dashboard_wsgi_app(biomarkers_context=context)

        # "ferritin" is in the default registry, but repository is empty
        status, headers, body = call_app(app, trends_path("ferritin"))
        assert status == "200 OK"
        assert "application/json" in headers.get("content-type", "")

        payload = json.loads(body.decode("utf-8"))
        assert payload["canonical_code"] == "ferritin"
        assert payload["first_value"] is None
        assert payload["latest_value"] is None
        assert payload["absolute_change"] is None
        assert payload["relative_change"] is None
        assert payload["direction"] == "insufficient_data"
        assert payload["strength"] == "none"
        assert payload["window"] == "all_time"
        assert payload["observations"] == 0

    def test_valid_trend_calculation_returns_200(self) -> None:
        context = BiomarkersApplicationContext()
        # Ingest two observations for ferritin
        _ingest_row(context, "0 | Ferrytyna | 50.0 | ng/mL | 15-300")
        # Same report or different report with a later date
        # Note: Ingest run creates observations.
        # To get distinct dates, we can ingest multiple reports or rows
        # Let's ingest two distinct rows
        _ingest_row(context, "1 | Ferrytyna | 150.0 | ng/mL | 15-300")

        app = create_dashboard_wsgi_app(biomarkers_context=context)
        status, headers, body = call_app(app, trends_path("ferritin"))

        assert status == "200 OK"
        assert "application/json" in headers.get("content-type", "")

        payload = json.loads(body.decode("utf-8"))
        assert payload["canonical_code"] == "ferritin"
        assert payload["first_value"] == 50.0
        assert payload["latest_value"] == 150.0
        assert payload["absolute_change"] == 100.0
        assert payload["relative_change"] == 200.0  # ((150 - 50)/50) * 100
        assert payload["direction"] == "increasing"
        assert payload["strength"] == "strong"
        assert payload["window"] == "all_time"
        assert payload["observations"] == 2

    def test_privacy_audit_for_trends(self) -> None:
        context = BiomarkersApplicationContext()
        _ingest_row(context, "0 | Ferrytyna | 50.0 | ng/mL | 15-300")

        app = create_dashboard_wsgi_app(biomarkers_context=context)
        status, _, body = call_app(app, trends_path("ferritin"))
        assert status == "200 OK"

        payload_str = body.decode("utf-8")
        forbidden = [
            "observation_id",
            "report_id",
            "import_run_id",
            "source_document_hash",
            "filename",
            "original_filename",
            "raw_value",
        ]
        for field in forbidden:
            assert field not in payload_str
