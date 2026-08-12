import json
import duckdb
import pytest

from decision import (
    DecisionHistoryProviderError,
    DuckDbDecisionAuditRecordRepository,
    EmptyDecisionHistoryProvider,
    RepositoryDecisionHistoryProvider,
)
from server.app import create_dashboard_wsgi_app, create_production_dashboard_wsgi_app
from tests.decision.test_decision_record_codec import build_sample_record
from tests.server.test_decision_intelligence_v2_endpoint import make_request


def test_get_decision_history_neutral_wsgi_app_returns_200_empty():
    app = create_dashboard_wsgi_app()

    status, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/history")
    assert status == 200

    data = json.loads(body)
    assert data == {
        "history": {
            "records": [],
            "count": 0,
        }
    }


def test_get_decision_history_with_records(tmp_path):
    db_file = tmp_path / "hist_test.duckdb"
    repo = DuckDbDecisionAuditRecordRepository(db_path=str(db_file))

    rec1 = build_sample_record("hist-ep-01")
    rec2 = build_sample_record("hist-ep-02")
    repo.save(rec1)
    repo.save(rec2)

    app = create_production_dashboard_wsgi_app(
        decision_db_path=str(db_file),
        activity_reconciliation_db_path=tmp_path / "reconciliation.duckdb",
    )

    status, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/history")
    assert status == 200

    data = json.loads(body)
    assert data["history"]["count"] == 2
    assert len(data["history"]["records"]) == 2
    assert data["history"]["records"][0]["decision_id"] == "hist-ep-01"
    assert data["history"]["records"][1]["decision_id"] == "hist-ep-02"


def test_get_decision_history_provider_error_returns_503():
    class FailingHistoryProvider:
        def get_history(self):
            raise DecisionHistoryProviderError("DB offline")

    app = create_dashboard_wsgi_app(decision_history_provider=FailingHistoryProvider())

    status, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/history")
    assert status == 503

    data = json.loads(body)
    assert "temporarily unavailable" in data["error"]
