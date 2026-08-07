from datetime import datetime, timezone
import json
import duckdb
import pytest

from decision import (
    DuckDbDecisionAuditRecordRepository,
    create_persisted_decision_runtime_application,
)
from server.app import create_dashboard_wsgi_app
from tests.decision.test_decision_record_codec import build_sample_record
from tests.decision.test_decision_runtime_composition import (
    CountingMorningBriefingProvider,
    CountingPerformanceProvider,
)
from tests.server.test_decision_intelligence_v2_endpoint import make_request



def test_persisted_decision_latest_endpoint_integration():
    conn = duckdb.connect(":memory:")
    repo = DuckDbDecisionAuditRecordRepository(conn=conn)
    mb_provider = CountingMorningBriefingProvider()
    perf_provider = CountingPerformanceProvider()

    app_runtime = create_persisted_decision_runtime_application(
        morning_briefing_provider=mb_provider,
        performance_test_provider=perf_provider,
        repository=repo,
    )

    wsgi_app = create_dashboard_wsgi_app(decision_audit_provider=app_runtime.latest_provider)

    # 1. Before workflow.run() -> GET /api/v1/decision-intelligence/latest returns 200 {"decision": null}
    status, headers, body = make_request(wsgi_app, "GET", "/api/v1/decision-intelligence/latest")
    assert status == 200
    data = json.loads(body)
    assert data["decision"] is None

    # 2. Run workflow explicitly
    result = app_runtime.workflow.run()

    # 3. After workflow.run() -> GET /api/v1/decision-intelligence/latest returns 200 with persisted decision record
    status, headers, body = make_request(wsgi_app, "GET", "/api/v1/decision-intelligence/latest")
    assert status == 200
    data = json.loads(body)
    assert data["decision"] is not None
    assert data["decision"]["decision_id"] == result.record.decision_id
    assert data["decision"]["policy_result"]["action"] == result.record.policy_result.action.value

    # 4. Repeated GET does not trigger decision execution
    status2, headers2, body2 = make_request(wsgi_app, "GET", "/api/v1/decision-intelligence/latest")
    assert status2 == 200
    data2 = json.loads(body2)
    assert data2["decision"]["decision_id"] == result.record.decision_id
    assert mb_provider.call_count == 4  # Still 4 calls from step 2
    assert perf_provider.call_count == 1  # Still 1 call from step 2


def test_create_dashboard_wsgi_app_is_purely_neutral_no_db_io():
    # Calling create_dashboard_wsgi_app without DI defaults to EmptyDecisionAuditRecordProvider
    app = create_dashboard_wsgi_app()
    status, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/latest")
    assert status == 200
    data = json.loads(body)
    assert data["decision"] is None


def test_app_instances_isolation(tmp_path):
    db1 = tmp_path / "app1.duckdb"
    db2 = tmp_path / "app2.duckdb"

    repo1 = DuckDbDecisionAuditRecordRepository(db_path=str(db1))
    repo2 = DuckDbDecisionAuditRecordRepository(db_path=str(db2))

    from decision.repository_audit_provider import RepositoryDecisionAuditRecordProvider
    app1 = create_dashboard_wsgi_app(decision_audit_provider=RepositoryDecisionAuditRecordProvider(repo1))
    app2 = create_dashboard_wsgi_app(decision_audit_provider=RepositoryDecisionAuditRecordProvider(repo2))

    rec1 = build_sample_record("rec-app-01")
    repo1.save(rec1)

    status1, headers1, body1 = make_request(app1, "GET", "/api/v1/decision-intelligence/latest")
    status2, headers2, body2 = make_request(app2, "GET", "/api/v1/decision-intelligence/latest")

    assert json.loads(body1)["decision"]["decision_id"] == "rec-app-01"
    assert json.loads(body2)["decision"] is None
