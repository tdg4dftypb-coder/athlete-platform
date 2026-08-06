from datetime import datetime, timezone
import json
from typing import Optional
from unittest.mock import MagicMock

import pytest

from morning_briefing.input_models import (
    MorningBriefingInput,
    RecoveryBriefingInput,
    TrainingBriefingInput,
    BiomarkerBriefingInput,
)
from morning_briefing.provider import (
    MorningBriefingInputProvider,
    MorningBriefingInputError,
    EmptyMorningBriefingInputProvider,
)
from server.app import create_dashboard_wsgi_app


# ── WSGI helper ───────────────────────────────────────────────────────────────

def call_app(app_fn, path: str, method: str = "GET") -> tuple[str, dict, bytes]:
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


ENDPOINT = "/api/v1/morning-briefing"

_FIXED_NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


# ── Stub providers ────────────────────────────────────────────────────────────

class _EmptyProvider:
    """Returns an all-None input (UNAVAILABLE result)."""
    def __init__(self, now=_FIXED_NOW):
        self._now = now

    def get_input(self) -> MorningBriefingInput:
        return MorningBriefingInput(
            generated_at=self._now,
            recovery=None,
            training=None,
            biomarkers=None,
        )


class _FullReadyProvider:
    """Returns full input with recovery score >= 70 → READY + 'Proceed as planned'."""
    def get_input(self) -> MorningBriefingInput:
        return MorningBriefingInput(
            generated_at=_FIXED_NOW,
            recovery=RecoveryBriefingInput(score=85, status="Good", summary="All good.", is_stale=False),
            training=TrainingBriefingInput(
                title="Easy run",
                description="Low intensity aerobic.",
                duration_minutes=45,
                intensity="low",
                is_available=True,
            ),
            biomarkers=BiomarkerBriefingInput(available_count=5, attention_count=0, summary="Normal.", is_stale=False),
        )


class _LowRecoveryAttentionBiomarkersProvider:
    """Recovery score < 50 + biomarkers attention_count > 0 — full pipeline check."""
    def get_input(self) -> MorningBriefingInput:
        return MorningBriefingInput(
            generated_at=_FIXED_NOW,
            recovery=RecoveryBriefingInput(score=30, status="Poor", summary="Rest needed.", is_stale=False),
            training=None,
            biomarkers=BiomarkerBriefingInput(available_count=3, attention_count=2, summary="Attention required.", is_stale=False),
        )


class _StaleProvider:
    """Returns stale recovery data."""
    def get_input(self) -> MorningBriefingInput:
        return MorningBriefingInput(
            generated_at=_FIXED_NOW,
            recovery=RecoveryBriefingInput(score=70, status="Good", summary="Summary.", is_stale=True),
            training=None,
            biomarkers=None,
        )


class _ErrorProvider:
    """Raises MorningBriefingInputError."""
    def get_input(self) -> MorningBriefingInput:
        raise MorningBriefingInputError("Source unavailable")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestMorningBriefingEndpoint:

    def test_returns_200(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_EmptyProvider())
        status, _, _ = call_app(app, ENDPOINT)
        assert status == "200 OK"

    def test_content_type_json(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_EmptyProvider())
        _, headers, _ = call_app(app, ENDPOINT)
        assert "application/json" in headers.get("content-type", "")

    def test_top_level_keys(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_EmptyProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        assert set(payload.keys()) == {"generated_at", "status", "sections"}

    def test_no_data_returns_unavailable_with_empty_sections(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_EmptyProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        assert payload["status"] == "unavailable"
        assert payload["sections"] == []

    def test_generated_at_is_iso_8601(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_EmptyProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        # Should be parseable as ISO 8601
        dt = datetime.fromisoformat(payload["generated_at"])
        assert isinstance(dt, datetime)

    def test_enums_as_lowercase_strings(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_FullReadyProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        assert isinstance(payload["status"], str)
        assert payload["status"] == payload["status"].lower()

    def test_full_ready_briefing_three_sections(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_FullReadyProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        assert payload["status"] == "ready"
        assert len(payload["sections"]) == 3
        titles = [s["title"] for s in payload["sections"]]
        assert "Recovery" in titles
        assert "Training" in titles
        assert "Biomarkers" in titles

    def test_recommendations_present_after_pipeline(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_FullReadyProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        recovery_section = next(s for s in payload["sections"] if s["title"] == "Recovery")
        rec_titles = [r["title"] for r in recovery_section["recommendations"]]
        assert "Proceed as planned" in rec_titles

    def test_priority_as_lowercase(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_FullReadyProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        recovery_section = next(s for s in payload["sections"] if s["title"] == "Recovery")
        for rec in recovery_section["recommendations"]:
            assert rec["priority"] == rec["priority"].lower()

    def test_none_passes_through_to_json_null(self) -> None:
        """Metric with None value should produce null in JSON."""
        app = create_dashboard_wsgi_app(morning_briefing_provider=_EmptyProvider())
        # Empty briefing has no sections — we use full provider but override recovery score to None
        class _NoneScoreProvider:
            def get_input(self):
                return MorningBriefingInput(
                    generated_at=_FIXED_NOW,
                    recovery=RecoveryBriefingInput(score=None, status=None, summary="No data.", is_stale=False),
                    training=None,
                    biomarkers=None,
                )
        app2 = create_dashboard_wsgi_app(morning_briefing_provider=_NoneScoreProvider())
        _, _, body = call_app(app2, ENDPOINT)
        payload = json.loads(body)
        recovery = next(s for s in payload["sections"] if s["title"] == "Recovery")
        score_metric = next(m for m in recovery["metrics"] if m["title"] == "Recovery score")
        assert score_metric["value"] is None

    def test_stale_input_returns_stale_status(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_StaleProvider())
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)
        assert payload["status"] == "stale"

    def test_provider_is_called_exactly_once(self) -> None:
        mock_provider = MagicMock()
        mock_provider.get_input.return_value = MorningBriefingInput(
            generated_at=_FIXED_NOW, recovery=None, training=None, biomarkers=None
        )
        app = create_dashboard_wsgi_app(morning_briefing_provider=mock_provider)
        call_app(app, ENDPOINT)
        mock_provider.get_input.assert_called_once()

    def test_provider_error_returns_503(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_ErrorProvider())
        status, _, body = call_app(app, ENDPOINT)
        assert status == "503 Service Unavailable"
        payload = json.loads(body)
        assert "error" in payload

    def test_503_error_does_not_leak_technical_details(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_ErrorProvider())
        _, _, body = call_app(app, ENDPOINT)
        text = body.decode("utf-8")
        assert "Traceback" not in text
        assert "Source unavailable" not in text
        assert ".py" not in text

    def test_no_python_enum_objects_in_response(self) -> None:
        app = create_dashboard_wsgi_app(morning_briefing_provider=_FullReadyProvider())
        _, _, body = call_app(app, ENDPOINT)
        # If body is valid JSON with no Enum objects, json.loads succeeds cleanly
        payload = json.loads(body)
        assert isinstance(payload["status"], str)
        # Verify no raw enum repr in text
        assert "MorningStatus." not in body.decode()
        assert "MorningPriority." not in body.decode()


class TestMorningBriefingFullPipeline:
    """Integration test: low recovery + biomarkers with attention → full recommendation pipeline."""

    def test_low_recovery_and_biomarker_attention_produces_expected_recommendations(self) -> None:
        app = create_dashboard_wsgi_app(
            morning_briefing_provider=_LowRecoveryAttentionBiomarkersProvider()
        )
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)

        # Status: partial (recovery + biomarkers but no training)
        assert payload["status"] == "partial"

        rec_titles = []
        for section in payload["sections"]:
            for rec in section["recommendations"]:
                rec_titles.append(rec["title"])

        assert "Prioritize recovery" in rec_titles
        assert "Review laboratory results" in rec_titles

    def test_low_recovery_recommendation_has_high_priority(self) -> None:
        app = create_dashboard_wsgi_app(
            morning_briefing_provider=_LowRecoveryAttentionBiomarkersProvider()
        )
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)

        recovery_section = next(s for s in payload["sections"] if s["title"] == "Recovery")
        prioritize_rec = next(
            r for r in recovery_section["recommendations"] if r["title"] == "Prioritize recovery"
        )
        assert prioritize_rec["priority"] == "high"

    def test_biomarker_recommendation_has_high_priority(self) -> None:
        app = create_dashboard_wsgi_app(
            morning_briefing_provider=_LowRecoveryAttentionBiomarkersProvider()
        )
        _, _, body = call_app(app, ENDPOINT)
        payload = json.loads(body)

        bio_section = next(s for s in payload["sections"] if s["title"] == "Biomarkers")
        review_rec = next(
            r for r in bio_section["recommendations"] if r["title"] == "Review laboratory results"
        )
        assert review_rec["priority"] == "high"
