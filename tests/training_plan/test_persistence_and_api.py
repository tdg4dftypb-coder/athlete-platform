"""Unit tests for Stage 26.4 persistence, repositories, provider, codecs, serializers, and WSGI endpoints."""
from datetime import date, datetime, timezone
import json
from pathlib import Path

import pytest

from application.training_plan_reconciliation import DailyTrainingReconciler
from decision.history_v2 import DecisionAuditRecord
from decision.context import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    ContextDataStatus,
    PerformanceDecisionContext,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)
from decision.policy_v2 import (
    DecisionAction,
    DecisionPolicyResult,
    DecisionPolicySignal,
    DecisionSeverity,
)
from decision.recommendation_plan import RecommendationPlanBuilder
from server.app import (
    create_dashboard_wsgi_app,
    create_production_dashboard_wsgi_app,
)
from training_plan.builder import BaselineTrainingPlanBuilder
from training_plan.history import (
    RepositoryPrescriptionHistoryProvider,
    RepositoryTrainingPlanHistoryProvider,
)
from training_plan.intent import (
    TrainingIntent,
    Weekday,
    WeeklySessionIntent,
)
from training_plan.models import (
    PlannedSession,
    PlannedSessionKind,
    TrainingPlan,
)
from training_plan.persistence.codecs import (
    FinalSessionPrescriptionCodec,
    TrainingPlanCodec,
)
from training_plan.persistence.duckdb_repository import (
    DuckDbFinalSessionPrescriptionRepository,
    DuckDbTrainingPlanRepository,
)

from training_plan.persistence.paths import get_default_training_plan_db_path
from training_plan.prescription import (
    FinalSessionPrescription,
    PrescriptionDisposition,
)
from training_plan.provider import RepositoryTrainingPlanProvider
from training_plan.repository import (
    TrainingPlanConflictError,
    TrainingPlanDataError,
)
from training_plan.serializers import (
    FinalSessionPrescriptionSerializer,
    TrainingPlanSerializer,
)


def make_test_plan(plan_id="plan-test-01", start_d=date(2026, 8, 10), version=1) -> TrainingPlan:
    end_d = date(start_d.year, start_d.month, start_d.day + 1)
    s1 = PlannedSession(f"{plan_id}:{start_d.isoformat()}", start_d, PlannedSessionKind.TRAINING, "VO2", 60, 70.0, "HIGH", 4, ("Intervals",))
    s2 = PlannedSession(f"{plan_id}:{end_d.isoformat()}", end_d, PlannedSessionKind.REST, None, 0, None, None, 1, ("Rest",))
    return TrainingPlan(
        plan_id=plan_id,
        start_date=start_d,
        end_date=end_d,
        version=version,
        generated_at=datetime(2026, 8, 7, 10, 0, tzinfo=timezone.utc),
        sessions=(s1, s2),
    )


def test_training_plan_codec_round_trips_canonical_multi_session_plan():
    target = date(2026, 8, 16)
    swim = PlannedSession(
        "multi:swim", target, PlannedSessionKind.TRAINING, "SWIM", 45,
        25.0, "EASY", 2, ("Technique",),
    )
    ride = PlannedSession(
        "multi:ride", target, PlannedSessionKind.TRAINING, "ENDURANCE", 180,
        130.0, "MODERATE", 4, ("Long ride",),
    )
    plan = TrainingPlan(
        "multi", target, target, 1,
        datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc),
        (swim, ride),
    )

    decoded = TrainingPlanCodec().decode(TrainingPlanCodec().encode(plan))

    assert decoded == plan
    assert tuple(session.session_id for session in decoded.sessions) == (
        "multi:ride",
        "multi:swim",
    )


def make_test_decision_record(decision_id: str, action: DecisionAction) -> DecisionAuditRecord:
    rec_at = datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc)
    sig = DecisionPolicySignal("SIG_TEST", "test", DecisionSeverity.MEDIUM, "Summary")
    res = DecisionPolicyResult(rec_at, action, DecisionSeverity.MEDIUM, (sig,), 0.9, "2.0")
    ctx = AthleteDecisionContext(
        generated_at=rec_at,
        recovery=RecoveryDecisionContext(ContextDataStatus.AVAILABLE, generated_at=rec_at),
        training=TrainingDecisionContext(ContextDataStatus.AVAILABLE, generated_at=rec_at),
        biomarkers=BiomarkerDecisionContext(ContextDataStatus.AVAILABLE, 0, 0, generated_at=rec_at),
        performance=PerformanceDecisionContext(ContextDataStatus.UNAVAILABLE),
    )
    plan = RecommendationPlanBuilder().build(res)
    return DecisionAuditRecord(decision_id, rec_at, ctx, res, plan)


def test_paths_resolver_priority(tmp_path, monkeypatch):
    # 1. Override path priority
    override = tmp_path / "custom.duckdb"
    assert get_default_training_plan_db_path(override) == override

    # 2. Env var priority
    env_target = tmp_path / "env.duckdb"
    monkeypatch.setenv("TRAINING_PLAN_DB_PATH", str(env_target))
    assert get_default_training_plan_db_path() == env_target


def test_training_plan_duckdb_repository_crud(tmp_path):
    db_file = tmp_path / "tp.duckdb"
    repo = DuckDbTrainingPlanRepository(db_path=db_file)

    plan1 = make_test_plan("p1")
    repo.save(plan1)

    # Idempotent re-save exact payload
    repo.save(plan1)

    # Conflict on same plan_id with different version/payload
    plan1_alt = make_test_plan("p1", version=2)
    with pytest.raises(TrainingPlanConflictError):
        repo.save(plan1_alt)

    # get_by_id
    retrieved = repo.get_by_id("p1")
    assert retrieved == plan1

    # get_latest
    assert repo.get_latest() == plan1

    # get_for_date
    assert repo.get_for_date(date(2026, 8, 10)) == plan1
    assert repo.get_for_date(date(2026, 8, 12)) is None

    # list_records
    assert len(repo.list_records()) == 1


def test_prescription_duckdb_repository_crud(tmp_path):
    db_file = tmp_path / "tp.duckdb"
    tp_repo = DuckDbTrainingPlanRepository(db_path=db_file)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=db_file)

    plan = make_test_plan("p1")
    tp_repo.save(plan)

    dec_rec = make_test_decision_record("dec-1", DecisionAction.REDUCE)
    reconciler = DailyTrainingReconciler()
    rx = reconciler.reconcile(plan.plan_id, plan.sessions[0], dec_rec)

    rx_repo.save(rx)

    # Idempotent re-save
    rx_repo.save(rx)

    # Conflict on duplicate natural key
    rx_alt = reconciler.reconcile(plan.plan_id, plan.sessions[0], make_test_decision_record("dec-1", DecisionAction.PROCEED))
    with pytest.raises(TrainingPlanConflictError):
        rx_repo.save(rx_alt)

    assert rx_repo.get_by_id(rx.prescription_id) == rx
    assert rx_repo.get_latest() == rx
    assert len(rx_repo.list_records()) == 1


def test_repository_training_plan_provider(tmp_path):
    db_file = tmp_path / "tp.duckdb"
    repo = DuckDbTrainingPlanRepository(db_path=db_file)
    provider = RepositoryTrainingPlanProvider(repository=repo)

    plan = make_test_plan("p1", start_d=date(2026, 8, 10))
    repo.save(plan)

    # Applicable plan and session
    assert provider.get_plan_for_date(date(2026, 8, 10)) == plan
    s_training = provider.get_planned_session(date(2026, 8, 10))
    assert s_training is not None
    assert s_training.kind == PlannedSessionKind.TRAINING

    s_rest = provider.get_planned_session(date(2026, 8, 11))
    assert s_rest is not None
    assert s_rest.kind == PlannedSessionKind.REST

    # Date with no plan returns None
    assert provider.get_planned_session(date(2026, 8, 15)) is None


def test_wsgi_read_endpoints_and_empty_states(tmp_path):
    # Empty providers test WSGI app
    app = create_dashboard_wsgi_app()

    def request(path):
        env = {"PATH_INFO": path, "REQUEST_METHOD": "GET"}
        resp_data = {}

        def start_response(status, headers):
            resp_data["status"] = status
            resp_data["headers"] = headers

        body = app(env, start_response)
        resp_data["json"] = json.loads(body[0].decode("utf-8"))
        return resp_data

    # 1. GET /api/v1/training-plan/latest
    res_tp_latest = request("/api/v1/training-plan/latest")
    assert res_tp_latest["status"] == "200 OK"
    assert res_tp_latest["json"]["plan"] is None

    # 2. GET /api/v1/training-plan/history
    res_tp_hist = request("/api/v1/training-plan/history")
    assert res_tp_hist["status"] == "200 OK"
    assert res_tp_hist["json"]["history"]["count"] == 0

    # 3. GET /api/v1/training-plan/prescriptions/latest
    res_rx_latest = request("/api/v1/training-plan/prescriptions/latest")
    assert res_rx_latest["status"] == "200 OK"
    assert res_rx_latest["json"]["prescription"] is None

    # 4. GET /api/v1/training-plan/prescriptions/history
    res_rx_hist = request("/api/v1/training-plan/prescriptions/history")
    assert res_rx_hist["status"] == "200 OK"
    assert res_rx_hist["json"]["history"]["count"] == 0


def test_wsgi_read_endpoints_503_and_500_error_contracts():
    from training_plan.history import (
        PrescriptionHistoryProviderError,
        TrainingPlanHistoryProviderError,
    )

    class FailingTPHistoryProvider:
        def get_latest_plan(self):
            raise TrainingPlanHistoryProviderError("DB connection failed")
        def get_plan_history(self):
            raise TrainingPlanHistoryProviderError("DB read failed")

    class FailingRxHistoryProvider:
        def get_latest_prescription(self):
            raise PrescriptionHistoryProviderError("DB connection failed")
        def get_prescription_history(self):
            raise PrescriptionHistoryProviderError("DB read failed")

    class UnexpectedErrorProvider:
        def get_latest_plan(self):
            raise RuntimeError("Unexpected internal crash")
        def get_plan_history(self):
            raise RuntimeError("Unexpected internal crash")
        def get_latest_prescription(self):
            raise RuntimeError("Unexpected internal crash")
        def get_prescription_history(self):
            raise RuntimeError("Unexpected internal crash")

    # App with expected 503 provider errors
    app_503 = create_dashboard_wsgi_app(
        training_plan_history_provider=FailingTPHistoryProvider(),
        prescription_history_provider=FailingRxHistoryProvider(),
    )

    def req(app, path):
        env = {"PATH_INFO": path, "REQUEST_METHOD": "GET"}
        resp_data = {}

        def start_response(status, headers):
            resp_data["status"] = status
            resp_data["headers"] = headers

        body = app(env, start_response)
        resp_data["json"] = json.loads(body[0].decode("utf-8"))
        return resp_data

    # 1. TP Latest -> 503
    res1 = req(app_503, "/api/v1/training-plan/latest")
    assert res1["status"] == "503 Service Unavailable"
    assert "error" in res1["json"]

    # 2. TP History -> 503
    res2 = req(app_503, "/api/v1/training-plan/history")
    assert res2["status"] == "503 Service Unavailable"
    assert "error" in res2["json"]

    # 3. Rx Latest -> 503
    res3 = req(app_503, "/api/v1/training-plan/prescriptions/latest")
    assert res3["status"] == "503 Service Unavailable"
    assert "error" in res3["json"]

    # 4. Rx History -> 503
    res4 = req(app_503, "/api/v1/training-plan/prescriptions/history")
    assert res4["status"] == "503 Service Unavailable"
    assert "error" in res4["json"]

    # App with unexpected 500 provider errors
    app_500 = create_dashboard_wsgi_app(
        training_plan_history_provider=UnexpectedErrorProvider(),
        prescription_history_provider=UnexpectedErrorProvider(),
    )

    res500_tp = req(app_500, "/api/v1/training-plan/latest")
    assert res500_tp["status"] == "500 Internal Server Error"
    assert "error" in res500_tp["json"]

    res500_rx = req(app_500, "/api/v1/training-plan/prescriptions/latest")
    assert res500_rx["status"] == "500 Internal Server Error"
    assert "error" in res500_rx["json"]


def test_production_read_composition_with_isolated_db(tmp_path):
    db_file = tmp_path / "prod_tp.duckdb"
    tp_repo = DuckDbTrainingPlanRepository(db_path=db_file)
    rx_repo = DuckDbFinalSessionPrescriptionRepository(db_path=db_file)

    plan = make_test_plan("prod-plan", start_d=date(2026, 8, 10))
    tp_repo.save(plan)

    dec_rec = make_test_decision_record("dec-prod-1", DecisionAction.PROCEED)
    reconciler = DailyTrainingReconciler()
    rx = reconciler.reconcile(plan.plan_id, plan.sessions[0], dec_rec)
    rx_repo.save(rx)

    app = create_production_dashboard_wsgi_app(
        training_plan_db_path=db_file,
        decision_db_path=tmp_path / "dec.duckdb",
        biomarkers_db_path=tmp_path / "bio.duckdb",
        health_db_path=tmp_path / "health.duckdb",
    )

    def request(path):
        env = {"PATH_INFO": path, "REQUEST_METHOD": "GET"}
        resp_data = {}

        def start_response(status, headers):
            resp_data["status"] = status
            resp_data["headers"] = headers

        body = app(env, start_response)
        resp_data["json"] = json.loads(body[0].decode("utf-8"))
        return resp_data

    # Verify latest plan returned via HTTP
    res_plan = request("/api/v1/training-plan/latest")
    assert res_plan["status"] == "200 OK"
    assert res_plan["json"]["plan"]["plan_id"] == "prod-plan"

    # Verify latest prescription returned via HTTP
    res_rx = request("/api/v1/training-plan/prescriptions/latest")
    assert res_rx["status"] == "200 OK"
    assert res_rx["json"]["prescription"]["prescription_id"] == rx.prescription_id
