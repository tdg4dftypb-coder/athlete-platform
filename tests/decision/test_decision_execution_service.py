from datetime import datetime, timedelta, timezone
import pytest

from decision import (
    AthleteDecisionContext,
    AthleteDecisionContextBuilder,
    BiomarkerDecisionContext,
    ContextDataStatus,
    DecisionAction,
    DecisionAuditRecord,
    DecisionAuditRecordBuilder,
    DecisionExecutionRequest,
    DecisionExecutionResult,
    DecisionExecutionService,
    DecisionPolicyV2,
    DecisionSeverity,
    EmptyAthleteDecisionContextProvider,
    PerformanceDecisionContext,
    RecommendationPlanBuilder,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


class StubContextProvider:
    def __init__(self, context: AthleteDecisionContext) -> None:
        self.context = context
        self.call_count = 0
        self.last_generated_at = None

    def build_context(self, generated_at: datetime) -> AthleteDecisionContext:
        self.call_count += 1
        self.last_generated_at = generated_at
        return self.context


class ErrorContextProvider:
    def build_context(self, generated_at: datetime) -> AthleteDecisionContext:
        raise RuntimeError("Context provider failed")


def test_decision_execution_request_invariants():
    gen_at = datetime.now(timezone.utc)
    rec_at = gen_at + timedelta(seconds=10)

    req = DecisionExecutionRequest(decision_id="dec-01", generated_at=gen_at, recorded_at=rec_at)
    assert req.decision_id == "dec-01"
    assert req.generated_at == gen_at
    assert req.recorded_at == rec_at
    assert req == DecisionExecutionRequest(decision_id="dec-01", generated_at=gen_at, recorded_at=rec_at)
    assert "DecisionExecutionRequest" in repr(req)

    # Empty decision_id
    with pytest.raises(ValueError, match="decision_id must be non-empty"):
        DecisionExecutionRequest(decision_id="", generated_at=gen_at, recorded_at=rec_at)

    with pytest.raises(ValueError, match="decision_id must be non-empty"):
        DecisionExecutionRequest(decision_id="   ", generated_at=gen_at, recorded_at=rec_at)

    # Invalid datetime types
    with pytest.raises(TypeError, match="generated_at must be datetime"):
        DecisionExecutionRequest(decision_id="d1", generated_at="invalid", recorded_at=rec_at)  # type: ignore

    with pytest.raises(TypeError, match="recorded_at must be datetime"):
        DecisionExecutionRequest(decision_id="d1", generated_at=gen_at, recorded_at="invalid")  # type: ignore

    # Earlier recorded_at than generated_at is allowed
    rec_earlier = gen_at - timedelta(seconds=5)
    req_earlier = DecisionExecutionRequest(decision_id="d-earlier", generated_at=gen_at, recorded_at=rec_earlier)
    assert req_earlier.recorded_at == rec_earlier


def test_decision_execution_result_invariants():
    gen_at = datetime.now(timezone.utc)
    rec_at = gen_at + timedelta(seconds=5)
    req = DecisionExecutionRequest(decision_id="dec-res-01", generated_at=gen_at, recorded_at=rec_at)

    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)
    ctx = AthleteDecisionContextBuilder().build(generated_at=gen_at, recovery=rc, training=tc, biomarkers=bc, performance=pc)
    pol_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(pol_res)
    record = DecisionAuditRecordBuilder().build("dec-res-01", rec_at, ctx, pol_res, plan)

    res = DecisionExecutionResult(request=req, record=record)
    assert res.request == req
    assert res.record == record
    assert res == DecisionExecutionResult(request=req, record=record)
    assert "DecisionExecutionResult" in repr(res)

    # Mismatch decision_id
    req_wrong_id = DecisionExecutionRequest(decision_id="other-id", generated_at=gen_at, recorded_at=rec_at)
    with pytest.raises(ValueError, match="record.decision_id must match request.decision_id"):
        DecisionExecutionResult(request=req_wrong_id, record=record)

    # Mismatch generated_at
    req_wrong_gen = DecisionExecutionRequest(decision_id="dec-res-01", generated_at=gen_at + timedelta(minutes=1), recorded_at=rec_at)
    with pytest.raises(ValueError, match="record.context.generated_at must match request.generated_at"):
        DecisionExecutionResult(request=req_wrong_gen, record=record)


def test_execution_service_full_pipeline():
    gen_at = datetime.now(timezone.utc)
    rec_at = gen_at + timedelta(seconds=2)
    req = DecisionExecutionRequest(decision_id="pipe-01", generated_at=gen_at, recorded_at=rec_at)

    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)
    ctx = AthleteDecisionContextBuilder().build(generated_at=gen_at, recovery=rc, training=tc, biomarkers=bc, performance=pc)

    provider_stub = StubContextProvider(ctx)
    service = DecisionExecutionService(context_provider=provider_stub)

    result = service.execute(req)

    assert provider_stub.call_count == 1
    assert provider_stub.last_generated_at == gen_at
    assert result.request == req
    assert result.record.decision_id == "pipe-01"
    assert result.record.recorded_at == rec_at
    assert result.record.policy_result.action == DecisionAction.PROCEED
    assert result.record.policy_result.severity == DecisionSeverity.LOW
    assert result.record.policy_result.confidence == 0.6
    assert result.record.recommendation_plan.recommendations[0].code == "proceed_as_planned"


def test_execution_service_policy_scenarios():
    gen_at = datetime.now(timezone.utc)
    rec_at = gen_at + timedelta(seconds=1)

    # 1. REST / CRITICAL scenario
    rc_crit = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=20.0)
    tc_plan = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="INTERVALS")
    bc_clean = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc_clean = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)
    ctx_rest = AthleteDecisionContextBuilder().build(generated_at=gen_at, recovery=rc_crit, training=tc_plan, biomarkers=bc_clean, performance=pc_clean)

    service_rest = DecisionExecutionService(context_provider=StubContextProvider(ctx_rest))
    res_rest = service_rest.execute(DecisionExecutionRequest("rest-01", gen_at, rec_at))

    assert res_rest.record.policy_result.action == DecisionAction.REST
    assert res_rest.record.policy_result.severity == DecisionSeverity.CRITICAL

    # 2. REVIEW scenario with all unavailable data
    service_unavail = DecisionExecutionService(context_provider=EmptyAthleteDecisionContextProvider())
    res_unavail = service_unavail.execute(DecisionExecutionRequest("unavail-01", gen_at, rec_at))

    assert res_unavail.record.policy_result.action == DecisionAction.REVIEW
    assert res_unavail.record.policy_result.severity == DecisionSeverity.HIGH


def test_dependency_injection_custom_components():
    gen_at = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=90.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)
    ctx = AthleteDecisionContextBuilder().build(generated_at=gen_at, recovery=rc, training=tc, biomarkers=bc, performance=pc)

    provider = StubContextProvider(ctx)
    custom_policy = DecisionPolicyV2()
    custom_plan_builder = RecommendationPlanBuilder()
    custom_audit_builder = DecisionAuditRecordBuilder()

    service = DecisionExecutionService(
        context_provider=provider,
        policy=custom_policy,
        recommendation_builder=custom_plan_builder,
        audit_record_builder=custom_audit_builder,
    )

    req = DecisionExecutionRequest("custom-di", gen_at, gen_at)
    res = service.execute(req)
    assert res.record.decision_id == "custom-di"


def test_execution_service_statelessness_and_idempotency():
    gen_at = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)
    ctx = AthleteDecisionContextBuilder().build(generated_at=gen_at, recovery=rc, training=tc, biomarkers=bc, performance=pc)

    service = DecisionExecutionService(context_provider=StubContextProvider(ctx))
    req = DecisionExecutionRequest("idempotent-01", gen_at, gen_at)

    res1 = service.execute(req)
    res2 = service.execute(req)

    assert res1 == res2


def test_execution_service_error_propagation():
    service_err = DecisionExecutionService(context_provider=ErrorContextProvider())
    req = DecisionExecutionRequest("err-01", datetime.now(timezone.utc), datetime.now(timezone.utc))

    with pytest.raises(RuntimeError, match="Context provider failed"):
        service_err.execute(req)


def test_architecture_dependency_isolation():
    import importlib
    import inspect

    mod = importlib.import_module('decision.execution_service')
    source = inspect.getsource(mod)

    prohibited = [
        "recovery", "training", "biomarkers", "performance_lab", "morning_briefing",
        "workout", "server", "duckdb", "sqlite", "json", "pathlib", "uuid", "DecisionEngine"
    ]
    for line in source.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("import ") or line_clean.startswith("from "):
            for p in prohibited:
                assert p not in line_clean, f"Prohibited import found in execution_service.py: {line_clean}"
