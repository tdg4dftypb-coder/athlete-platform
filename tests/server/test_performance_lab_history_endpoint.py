"""Tests for GET /api/v1/performance-lab/history endpoint — Sprint 21.6A."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest

from performance_lab.domain import (
    ExerciseModality,
    PerformanceStage,
    PerformanceTestSession,
    PerformanceTestStatus,
    PerformanceTestType,
    StageCompletionStatus,
)
from performance_lab.provider import (
    EmptyPerformanceTestSessionProvider,
    PerformanceTestSessionProviderError,
)
from server.app import create_dashboard_wsgi_app

TIME_1 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
TIME_2 = datetime(2026, 8, 5, 14, 0, 0, tzinfo=timezone.utc)


def make_session(
    test_id: str,
    performed_at: datetime = TIME_1,
    test_type: PerformanceTestType = PerformanceTestType.LACTATE_STEP_TEST,
    lactate_val: float | None = 2.1,
) -> PerformanceTestSession:
    stage = PerformanceStage(
        stage_number=1,
        completion_status=StageCompletionStatus.COMPLETED,
        duration_seconds=180,
        power_watts=150.0,
        speed_kph=None,
        heart_rate_bpm=130,
        lactate_mmol_l=lactate_val,
        cadence_rpm=88.0,
        perceived_exertion=4.0,
        notes=None,
    )
    return PerformanceTestSession(
        test_id=test_id,
        performed_at=performed_at,
        test_type=test_type,
        status=PerformanceTestStatus.COMPLETED,
        modality=ExerciseModality.CYCLING,
        stages=(stage,),
        protocol_name="Standard Step",
        body_mass_kg=70.0,
        ambient_temperature_c=20.0,
        notes=None,
    )


class StubWsgiResponse:
    def __init__(self) -> None:
        self.status: str = ""
        self.headers: list[tuple[str, str]] = []

    def start_response(self, status: str, headers: list[tuple[str, str]]) -> None:
        self.status = status
        self.headers = headers


def call_app(
    app: Any,
    path: str = "/api/v1/performance-lab/history",
    method: str = "GET",
) -> tuple[int, dict[str, str], bytes]:
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
    }
    resp = StubWsgiResponse()
    body_chunks = app(environ, resp.start_response)
    body = b"".join(body_chunks)

    status_code = int(resp.status.split()[0])
    headers_dict = {k.lower(): v for k, v in resp.headers}
    return status_code, headers_dict, body


class TestPerformanceLabHistoryEndpoint:
    def test_default_empty_provider_returns_200_empty_entries(self) -> None:
        app = create_dashboard_wsgi_app()
        status_code, headers, body = call_app(app)

        assert status_code == 200
        assert "application/json" in headers.get("content-type", "")

        data = json.loads(body.decode("utf-8"))
        assert data == {"entries": []}

    def test_empty_provider_unit(self) -> None:
        provider = EmptyPerformanceTestSessionProvider()
        sessions = provider.get_sessions()
        assert sessions == ()
        assert isinstance(sessions, tuple)

    def test_injected_provider_single_call_and_data_flow(self) -> None:
        mock_provider = Mock()
        s1 = make_session("s1", TIME_1, PerformanceTestType.LACTATE_STEP_TEST)
        mock_provider.get_sessions.return_value = (s1,)

        app = create_dashboard_wsgi_app(performance_lab_provider=mock_provider)
        status_code, headers, body = call_app(app)

        assert status_code == 200
        assert mock_provider.get_sessions.call_count == 1

        data = json.loads(body.decode("utf-8"))
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["session"]["test_id"] == "s1"
        assert entry["lactate_curve"] is not None
        assert entry["threshold_analysis"] is not None
        assert entry["threshold_analysis"]["lt1"]["status"] == "detected"
        assert entry["threshold_analysis"]["lt2"]["status"] == "not_reached"

    def test_pipeline_deduplication_and_sorting(self) -> None:
        mock_provider = Mock()
        s1_old = make_session("dup_id", TIME_1)
        s1_new = make_session("dup_id", TIME_2)
        s2 = make_session("other_id", TIME_1)

        mock_provider.get_sessions.return_value = (s1_old, s1_new, s2)

        app = create_dashboard_wsgi_app(performance_lab_provider=mock_provider)
        status_code, _, body = call_app(app)

        assert status_code == 200
        data = json.loads(body.decode("utf-8"))

        # Deduplicated to 2 entries, sorted TIME_1 then TIME_2
        assert len(data["entries"]) == 2
        assert data["entries"][0]["session"]["test_id"] == "other_id"
        assert data["entries"][1]["session"]["test_id"] == "dup_id"
        assert data["entries"][1]["session"]["performed_at"] == TIME_2.isoformat()

    def test_deduplication_same_performed_at_selects_last_input_occurrence(self) -> None:
        mock_provider = Mock()
        s1 = make_session("dup_id", TIME_1, lactate_val=1.5)
        s2 = make_session("dup_id", TIME_1, lactate_val=3.5)

        mock_provider.get_sessions.return_value = (s1, s2)

        app = create_dashboard_wsgi_app(performance_lab_provider=mock_provider)
        status_code, _, body = call_app(app)

        assert status_code == 200
        data = json.loads(body.decode("utf-8"))
        assert len(data["entries"]) == 1
        # Selected s2 stage value 3.5
        assert data["entries"][0]["session"]["stages"][0]["lactate_mmol_l"] == 3.5

    def test_ftp_test_in_history_has_null_curve_and_thresholds(self) -> None:
        mock_provider = Mock()
        # Stage has lactate_val=4.2, but test_type is FTP_TEST
        s_ftp = make_session("ftp1", TIME_1, PerformanceTestType.FTP_TEST, lactate_val=4.2)
        mock_provider.get_sessions.return_value = (s_ftp,)

        app = create_dashboard_wsgi_app(performance_lab_provider=mock_provider)
        status_code, _, body = call_app(app)

        assert status_code == 200
        data = json.loads(body.decode("utf-8"))
        entry = data["entries"][0]
        assert entry["session"]["test_type"] == "ftp_test"
        assert entry["lactate_curve"] is None
        assert entry["threshold_analysis"] is None

    def test_provider_error_returns_safe_503(self) -> None:
        mock_provider = Mock()
        mock_provider.get_sessions.side_effect = PerformanceTestSessionProviderError(
            "Database connection failed: internal details SELECT * FROM private_table"
        )

        app = create_dashboard_wsgi_app(performance_lab_provider=mock_provider)
        status_code, headers, body = call_app(app)

        assert status_code == 503
        data = json.loads(body.decode("utf-8"))

        # Strict error contract
        assert data == {"error": "Performance Lab data source is temporarily unavailable."}
        raw_text = body.decode("utf-8")
        forbidden = ["Database connection failed", "SELECT", "private_table", "Traceback"]
        for word in forbidden:
            assert word not in raw_text

    def test_options_cors_preflight(self) -> None:
        app = create_dashboard_wsgi_app()
        status_code, headers, body = call_app(app, method="OPTIONS")

        assert status_code == 204
        assert headers.get("access-control-allow-origin") == "*"
        assert "GET" in headers.get("access-control-allow-methods", "")

    def test_provider_instance_isolation(self) -> None:
        prov1 = Mock()
        prov1.get_sessions.return_value = (make_session("s1"),)

        prov2 = Mock()
        prov2.get_sessions.return_value = (make_session("s2"),)

        app1 = create_dashboard_wsgi_app(performance_lab_provider=prov1)
        app2 = create_dashboard_wsgi_app(performance_lab_provider=prov2)

        _, _, body1 = call_app(app1)
        _, _, body2 = call_app(app2)

        data1 = json.loads(body1.decode("utf-8"))
        data2 = json.loads(body2.decode("utf-8"))

        assert data1["entries"][0]["session"]["test_id"] == "s1"
        assert data2["entries"][0]["session"]["test_id"] == "s2"

    def test_no_private_or_internal_fields_exposed(self) -> None:
        mock_provider = Mock()
        mock_provider.get_sessions.return_value = (make_session("s1"),)

        app = create_dashboard_wsgi_app(performance_lab_provider=mock_provider)
        _, _, body = call_app(app)
        raw_text = body.decode("utf-8")

        forbidden_keys = [
            "filename",
            "source_document_hash",
            "database_id",
            "observation_id",
            "raw_payload",
            "PerformanceTestSession",
        ]
        for key in forbidden_keys:
            assert key not in raw_text
