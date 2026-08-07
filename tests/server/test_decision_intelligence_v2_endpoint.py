from datetime import datetime, timezone
import json
import pytest

from decision import (
    AthleteDecisionContextBuilder,
    BiomarkerDecisionContext,
    ContextDataStatus,
    DecisionAuditRecordBuilder,
    DecisionAuditRecordProviderError,
    DecisionPolicyV2,
    PerformanceDecisionContext,
    RecommendationPlanBuilder,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)
from server.app import create_dashboard_wsgi_app


def build_stub_record():
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    ctx = AthleteDecisionContextBuilder().build(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)
    res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(res)
    return DecisionAuditRecordBuilder().build("dec-endpoint-01", now, ctx, res, plan)


class StubDecisionAuditRecordProvider:
    def __init__(self, record=None, raise_error=False):
        self.record = record
        self.raise_error = raise_error
        self.call_count = 0

    def get_latest_record(self):
        self.call_count += 1
        if self.raise_error:
            raise DecisionAuditRecordProviderError("Data source offline")
        return self.record


def make_request(app, method="GET", path="/api/v1/decision-intelligence/latest"):
    responses = []

    def start_response(status, headers):
        responses.append((status, headers))

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
    }

    body_bytes_list = app(environ, start_response)
    status_str, headers_list = responses[0]
    status_code = int(status_str.split(" ")[0])
    body_str = b"".join(body_bytes_list).decode("utf-8")
    return status_code, headers_list, body_str


def test_get_latest_decision_none_returns_200_null():
    provider = StubDecisionAuditRecordProvider(record=None)
    app = create_dashboard_wsgi_app(decision_audit_provider=provider)

    status_code, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/latest")

    assert status_code == 200
    assert provider.call_count == 1

    header_dict = dict(headers)
    assert "application/json" in header_dict["Content-Type"]

    data = json.loads(body)
    assert data == {"decision": None}


def test_get_latest_decision_present_returns_200_payload():
    record = build_stub_record()
    provider = StubDecisionAuditRecordProvider(record=record)
    app = create_dashboard_wsgi_app(decision_audit_provider=provider)

    status_code, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/latest")

    assert status_code == 200
    assert provider.call_count == 1

    data = json.loads(body)
    assert "decision" in data
    dec = data["decision"]
    assert dec["decision_id"] == "dec-endpoint-01"
    assert dec["policy_result"]["action"] == "proceed"
    assert dec["recommendation_plan"]["recommendations"][0]["code"] == "proceed_as_planned"


def test_get_latest_decision_provider_error_returns_503():
    provider = StubDecisionAuditRecordProvider(raise_error=True)
    app = create_dashboard_wsgi_app(decision_audit_provider=provider)

    status_code, headers, body = make_request(app, "GET", "/api/v1/decision-intelligence/latest")

    assert status_code == 503
    data = json.loads(body)
    assert data == {"error": "Decision Intelligence data source is temporarily unavailable."}
    assert "Data source offline" not in body  # Raw error message is hidden


def test_dependency_injection_isolation():
    rec1 = build_stub_record()
    p1 = StubDecisionAuditRecordProvider(record=rec1)
    p2 = StubDecisionAuditRecordProvider(record=None)

    app1 = create_dashboard_wsgi_app(decision_audit_provider=p1)
    app2 = create_dashboard_wsgi_app(decision_audit_provider=p2)

    _, _, body1 = make_request(app1)
    _, _, body2 = make_request(app2)

    assert json.loads(body1)["decision"]["decision_id"] == "dec-endpoint-01"
    assert json.loads(body2)["decision"] is None


def test_options_preflight_cors():
    app = create_dashboard_wsgi_app()
    status_code, headers, body = make_request(app, "OPTIONS", "/api/v1/decision-intelligence/latest")

    assert status_code == 204
    header_dict = dict(headers)
    assert header_dict.get("Access-Control-Allow-Origin") == "*"


def test_no_on_demand_decision_execution(monkeypatch):
    record = build_stub_record()

    # Verify that requesting the endpoint does NOT invoke DecisionPolicyV2.evaluate
    eval_called = False

    def mock_evaluate(*args, **kwargs):
        nonlocal eval_called
        eval_called = True
        raise RuntimeError("DecisionPolicyV2 should NOT be called during HTTP request!")

    monkeypatch.setattr("decision.policy_v2.DecisionPolicyV2.evaluate", mock_evaluate)

    provider = StubDecisionAuditRecordProvider(record=record)
    app = create_dashboard_wsgi_app(decision_audit_provider=provider)

    status_code, _, body = make_request(app, "GET", "/api/v1/decision-intelligence/latest")

    assert status_code == 200
    assert not eval_called
    assert json.loads(body)["decision"]["decision_id"] == "dec-endpoint-01"
