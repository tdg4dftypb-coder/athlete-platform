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


def insights_path(canonical_code: str) -> str:
    return f"/api/v1/biomarkers/insights/{canonical_code}"


def _ingest_row(context: BiomarkersApplicationContext, row: str) -> None:
    content = row.encode("utf-8")
    res = context.ingestion_service.ingest(LaboratoryIngestionRequest(content=content))
    assert res.report is not None


class TestInsightsEndpoint:
    def test_unknown_canonical_code_returns_404(self) -> None:
        context = BiomarkersApplicationContext()
        app = create_dashboard_wsgi_app(biomarkers_context=context)

        status, _, body = call_app(app, insights_path("non_existent_code"))
        assert status == "404 Not Found"
        payload = json.loads(body.decode("utf-8"))
        assert "error" in payload

    def test_invalid_canonical_code_returns_400(self) -> None:
        context = BiomarkersApplicationContext()
        app = create_dashboard_wsgi_app(biomarkers_context=context)

        status, _, _ = call_app(app, insights_path("InvalidCode"))
        assert status == "400 Bad Request"

        status, _, _ = call_app(app, insights_path("code_with_spaces "))
        assert status == "400 Bad Request"

    def test_empty_history_for_valid_biomarker_returns_200_with_unknown_insight(self) -> None:
        context = BiomarkersApplicationContext()
        app = create_dashboard_wsgi_app(biomarkers_context=context)

        # "ferritin" is in registry, but repo is empty
        status, headers, body = call_app(app, insights_path("ferritin"))
        assert status == "200 OK"
        assert "application/json" in headers.get("content-type", "")

        payload = json.loads(body.decode("utf-8"))
        assert payload["canonical_code"] == "ferritin"
        assert payload["interpretation"] == "unknown"
        assert payload["confidence"] == "none"
        assert payload["summary"] == "Biomarker trend interpretation is unavailable."
        assert payload["reasoning"] == "Generic trend interpretation."

        # Nested trend validation
        assert isinstance(payload["trend"], dict)
        assert payload["trend"]["canonical_code"] == "ferritin"
        assert payload["trend"]["direction"] == "insufficient_data"
        assert payload["trend"]["observations"] == 0

    def test_valid_insight_for_ferritin_returns_200(self) -> None:
        context = BiomarkersApplicationContext()
        _ingest_row(context, "0 | Ferrytyna | 50.0 | ng/mL | 15-300")
        _ingest_row(context, "1 | Ferrytyna | 150.0 | ng/mL | 15-300")

        app = create_dashboard_wsgi_app(biomarkers_context=context)
        status, headers, body = call_app(app, insights_path("ferritin"))

        assert status == "200 OK"
        assert "application/json" in headers.get("content-type", "")

        payload = json.loads(body.decode("utf-8"))
        assert payload["canonical_code"] == "ferritin"
        assert payload["interpretation"] == "positive"  # FerritinRule increasing -> POSITIVE
        assert payload["confidence"] == "high"
        assert payload["summary"] == "Ferritin is improving."
        assert payload["reasoning"] == "Ferritin shows an increasing trend."

        # Nested trend validation
        assert payload["trend"]["first_value"] == 50.0
        assert payload["trend"]["latest_value"] == 150.0
        assert payload["trend"]["absolute_change"] == 100.0
        assert payload["trend"]["relative_change"] == 200.0
        assert payload["trend"]["direction"] == "increasing"
        assert payload["trend"]["strength"] == "strong"
        assert payload["trend"]["observations"] == 2

    def test_valid_insight_for_crp_returns_200(self) -> None:
        context = BiomarkersApplicationContext()
        _ingest_row(context, "0 | CRP | 5.0 | mg/L | 0-5")
        _ingest_row(context, "1 | CRP | 15.0 | mg/L | 0-5")  # increase

        app = create_dashboard_wsgi_app(biomarkers_context=context)
        status, _, body = call_app(app, insights_path("crp"))

        assert status == "200 OK"
        payload = json.loads(body.decode("utf-8"))
        assert payload["canonical_code"] == "crp"
        assert payload["interpretation"] == "negative"  # CRPRule increasing -> NEGATIVE
        assert payload["confidence"] == "high"
        assert payload["summary"] == "CRP is increasing."
        assert payload["reasoning"] == "An increasing CRP trend may indicate growing inflammation."

    def test_privacy_audit_for_insights(self) -> None:
        context = BiomarkersApplicationContext()
        _ingest_row(context, "0 | Ferrytyna | 50.0 | ng/mL | 15-300")

        app = create_dashboard_wsgi_app(biomarkers_context=context)
        status, _, body = call_app(app, insights_path("ferritin"))
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
