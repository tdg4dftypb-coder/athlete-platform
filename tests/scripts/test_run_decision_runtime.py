import duckdb
import pytest

from decision import (
    DuckDbDecisionAuditRecordRepository,
    create_persisted_decision_runtime_application,
)
from scripts.run_decision_runtime import run_decision_runtime
from server.app import create_dashboard_wsgi_app, create_production_dashboard_wsgi_app
from tests.decision.test_decision_record_codec import build_sample_record
from tests.decision.test_decision_runtime_composition import (
    CountingMorningBriefingProvider,
    CountingPerformanceProvider,
)
from tests.server.test_decision_intelligence_v2_endpoint import make_request


def test_cli_runner_executes_and_returns_zero(tmp_path, capsys):
    db_file = tmp_path / "cli_decisions.duckdb"
    mb_provider = CountingMorningBriefingProvider()
    perf_provider = CountingPerformanceProvider()

    exit_code = run_decision_runtime(
        db_path=str(db_file),
        morning_briefing_provider=mb_provider,
        performance_test_provider=perf_provider,
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Decision generated" in captured.out
    assert "Decision ID :" in captured.out
    assert "Action      : review" in captured.out
    assert "Severity    : high" in captured.out
    assert "Confidence  : 0.85" in captured.out


def test_full_pipeline_runner_db_get_integration(tmp_path):
    db_file = tmp_path / "integration_decisions.duckdb"

    # 1. Run CLI runner to generate decision with Empty providers (defaults)
    exit_code = run_decision_runtime(db_path=str(db_file))
    assert exit_code == 0

    # 2. Production WSGI app opening the same test database
    app = create_production_dashboard_wsgi_app(decision_db_path=str(db_file))

    # 3. GET /api/v1/decision-intelligence/latest returns saved REVIEW decision
    status, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/latest")
    assert status == 200
    import json
    data = json.loads(body)
    assert data["decision"] is not None
    assert data["decision"]["policy_result"]["action"] == "review"
    assert data["decision"]["policy_result"]["severity"] == "high"
    assert data["decision"]["policy_result"]["confidence"] == 0.85
