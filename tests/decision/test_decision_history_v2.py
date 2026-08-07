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
    DecisionExplanation,
    DecisionExplanationItem,
    DecisionHistory,
    DecisionHistoryBuilder,
    DecisionPolicyResult,
    DecisionPolicySignal,
    DecisionPolicyV2,
    DecisionRecommendation,
    DecisionSeverity,
    PerformanceDecisionContext,
    RecommendationCategory,
    RecommendationPlan,
    RecommendationPlanBuilder,
    RecommendationPriority,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


def build_sample_pipeline_record(
    decision_id: str,
    gen_time: datetime,
    rec_time: datetime,
    rec_score: float = 85.0,
) -> tuple[AthleteDecisionContext, DecisionPolicyResult, RecommendationPlan, DecisionAuditRecord]:
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=rec_score)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    builder_ctx = AthleteDecisionContextBuilder()
    ctx = builder_ctx.build(generated_at=gen_time, recovery=rc, training=tc, biomarkers=bc, performance=pc)

    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    plan_builder = RecommendationPlanBuilder()
    plan = plan_builder.build(res)

    audit_builder = DecisionAuditRecordBuilder()
    record = audit_builder.build(
        decision_id=decision_id,
        recorded_at=rec_time,
        context=ctx,
        policy_result=res,
        recommendation_plan=plan,
    )

    return ctx, res, plan, record


def test_decision_audit_record_valid_and_invariants():
    now = datetime.now(timezone.utc)
    rec_time = now + timedelta(seconds=5)
    ctx, res, plan, record = build_sample_pipeline_record("dec-001", now, rec_time)

    assert record.decision_id == "dec-001"
    assert record.recorded_at == rec_time
    assert record.context == ctx
    assert record.policy_result == res
    assert record.recommendation_plan == plan
    assert "DecisionAuditRecord" in repr(record)

    record_dup = DecisionAuditRecord(
        decision_id="dec-001",
        recorded_at=rec_time,
        context=ctx,
        policy_result=res,
        recommendation_plan=plan,
    )
    assert record == record_dup

    # Invalid decision_id
    with pytest.raises(ValueError, match="decision_id must be non-empty"):
        DecisionAuditRecord(decision_id="   ", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan)

    with pytest.raises(TypeError, match="recorded_at must be datetime"):
        DecisionAuditRecord(decision_id="d1", recorded_at="invalid", context=ctx, policy_result=res, recommendation_plan=plan)  # type: ignore


def test_decision_audit_record_mismatch_validations():
    now = datetime.now(timezone.utc)
    rec_time = now + timedelta(seconds=5)
    ctx, res, plan, record = build_sample_pipeline_record("dec-001", now, rec_time)

    # 1. Mismatch context/policy generated_at
    ctx_other = AthleteDecisionContextBuilder().build(
        generated_at=now + timedelta(minutes=1),
        recovery=ctx.recovery,
        training=ctx.training,
        biomarkers=ctx.biomarkers,
        performance=ctx.performance,
    )
    with pytest.raises(ValueError, match="policy_result.generated_at must match context.generated_at"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx_other, policy_result=res, recommendation_plan=plan)

    # 2. Mismatch policy/plan generated_at
    plan_other = RecommendationPlan(
        generated_at=now + timedelta(minutes=1),
        action=plan.action,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=plan.explanation,
    )
    with pytest.raises(ValueError, match="recommendation_plan.generated_at must match policy_result.generated_at"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan_other)

    # 3. Mismatch action
    plan_action_diff = RecommendationPlan(
        generated_at=now,
        action=DecisionAction.REST,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=plan.explanation,
    )
    with pytest.raises(ValueError, match="recommendation_plan.action must match policy_result.action"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan_action_diff)

    # 4. Mismatch severity
    plan_sev_diff = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=DecisionSeverity.CRITICAL,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=plan.explanation,
    )
    with pytest.raises(ValueError, match="recommendation_plan.severity must match policy_result.severity"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan_sev_diff)

    # 5. Mismatch confidence
    plan_conf_diff = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=plan.severity,
        confidence=0.99,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=plan.explanation,
    )
    with pytest.raises(ValueError, match="recommendation_plan.confidence must match policy_result.confidence"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan_conf_diff)

    # 6. Mismatch policy_version
    plan_ver_diff = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version="1.0",
        recommendations=plan.recommendations,
        explanation=plan.explanation,
    )
    with pytest.raises(ValueError, match="recommendation_plan.policy_version must match policy_result.policy_version"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan_ver_diff)

    # 7. Explanation items count mismatch
    exp_empty_item = DecisionExplanation(
        headline=plan.explanation.headline,
        summary=plan.explanation.summary,
        items=(
            plan.explanation.items[0],
            DecisionExplanationItem(signal_code="extra", source="src", severity=DecisionSeverity.LOW, summary="sum"),
        ),
    )
    plan_exp_diff = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=exp_empty_item,
    )
    with pytest.raises(ValueError, match="explanation.items count must match policy_result.signals count"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan_exp_diff)

    # 8. Mismatch signal code in explanation item
    exp_wrong_code = DecisionExplanation(
        headline=plan.explanation.headline,
        summary=plan.explanation.summary,
        items=(DecisionExplanationItem(signal_code="wrong_code", source=res.signals[0].source, severity=res.signals[0].severity, summary=res.signals[0].summary),),
    )
    plan_wrong_code = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=exp_wrong_code,
    )
    with pytest.raises(ValueError, match="signal_code 'wrong_code' does not match signal code"):
        DecisionAuditRecord(decision_id="d1", recorded_at=rec_time, context=ctx, policy_result=res, recommendation_plan=plan_wrong_code)


def test_record_builder_behavior():
    now = datetime.now(timezone.utc)
    rec_time = now + timedelta(seconds=10)
    ctx, res, plan, _ = build_sample_pipeline_record("d-builder", now, rec_time)

    builder = DecisionAuditRecordBuilder()
    rec1 = builder.build("d-builder", rec_time, ctx, res, plan)
    rec2 = builder.build("d-builder", rec_time, ctx, res, plan)

    assert rec1 == rec2
    assert rec1.decision_id == "d-builder"
    assert rec1.recorded_at == rec_time
    assert rec1.context == ctx
    assert rec1.policy_result == res
    assert rec1.recommendation_plan == plan


def test_decision_history_invariants():
    now = datetime.now(timezone.utc)
    _, _, _, rec1 = build_sample_pipeline_record("dec-001", now, now)
    _, _, _, rec2 = build_sample_pipeline_record("dec-002", now + timedelta(minutes=1), now + timedelta(minutes=1))

    # Valid empty & sorted
    dh_empty = DecisionHistory(records=())
    assert dh_empty.records == ()

    dh = DecisionHistory(records=(rec1, rec2))
    assert len(dh.records) == 2
    assert dh == DecisionHistory(records=(rec1, rec2))
    assert "DecisionHistory" in repr(dh)

    # Must be tuple
    with pytest.raises(TypeError, match="records must be tuple"):
        DecisionHistory(records=[rec1, rec2])  # type: ignore

    # Duplicate decision_id
    with pytest.raises(ValueError, match="Duplicate decision_id in history"):
        DecisionHistory(records=(rec1, rec1))

    # Unsorted records
    with pytest.raises(ValueError, match="records must be sorted chronologically"):
        DecisionHistory(records=(rec2, rec1))


def test_history_builder_sorting_and_deduplication():
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(minutes=10)
    t2 = t0 + timedelta(minutes=20)

    # Build unordered records with duplicates
    _, _, _, rec_t0 = build_sample_pipeline_record("dec-100", t0, t0)
    _, _, _, rec_t2 = build_sample_pipeline_record("dec-300", t2, t2)

    # Duplicate dec-200 with different recorded_at
    _, _, _, rec_t1_v1 = build_sample_pipeline_record("dec-200", t1, t1, rec_score=80.0)
    _, _, _, rec_t1_v2 = build_sample_pipeline_record("dec-200", t1, t1 + timedelta(seconds=30), rec_score=50.0)

    input_records = (rec_t2, rec_t1_v1, rec_t0, rec_t1_v2)

    builder = DecisionHistoryBuilder()
    history = builder.build(input_records)

    assert isinstance(history, DecisionHistory)
    assert len(history.records) == 3

    # Sorted oldest -> newest: dec-100 (t0) -> dec-200 (t1) -> dec-300 (t2)
    ids = [r.decision_id for r in history.records]
    assert ids == ["dec-100", "dec-200", "dec-300"]

    # Deduplication kept rec_t1_v2 because its recorded_at was later
    rec_dec200 = history.records[1]
    assert rec_dec200.policy_result.action == DecisionAction.REPLACE_WITH_RECOVERY  # rec_score=50.0

    # Same recorded_at tie-breaker -> last occurrence in input
    _, _, _, rec_dup1 = build_sample_pipeline_record("dup-id", t0, t0, rec_score=90.0)
    _, _, _, rec_dup2 = build_sample_pipeline_record("dup-id", t0, t0, rec_score=30.0)

    history_dup = builder.build((rec_dup1, rec_dup2))
    assert len(history_dup.records) == 1
    assert history_dup.records[0].policy_result.action == DecisionAction.REST  # rec_score=30.0 (rec_dup2)

    # Input tuple remains unmutated
    assert len(input_records) == 4


def test_full_pipeline_end_to_end_consistency():
    now = datetime.now(timezone.utc)
    rec_time = now + timedelta(seconds=1)

    # 1. AthleteDecisionContext
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=45.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="INTERVALS")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    ctx = AthleteDecisionContextBuilder().build(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)

    # 2. DecisionPolicyV2
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    # 3. RecommendationPlanBuilder
    plan = RecommendationPlanBuilder().build(res)

    # 4. DecisionAuditRecordBuilder
    record = DecisionAuditRecordBuilder().build(
        decision_id="full-pipe-01",
        recorded_at=rec_time,
        context=ctx,
        policy_result=res,
        recommendation_plan=plan,
    )

    # 5. DecisionHistoryBuilder
    history = DecisionHistoryBuilder().build((record,))

    assert len(history.records) == 1
    stored_rec = history.records[0]

    # Verify complete consistency across pipeline
    assert stored_rec.decision_id == "full-pipe-01"
    assert stored_rec.context.generated_at == now
    assert stored_rec.policy_result.action == DecisionAction.REPLACE_WITH_RECOVERY
    assert stored_rec.policy_result.severity == DecisionSeverity.HIGH
    assert stored_rec.policy_result.confidence == 0.85
    assert stored_rec.policy_result.policy_version == "2.0"

    assert stored_rec.recommendation_plan.action == stored_rec.policy_result.action
    assert stored_rec.recommendation_plan.severity == stored_rec.policy_result.severity
    assert stored_rec.recommendation_plan.confidence == stored_rec.policy_result.confidence
    assert stored_rec.recommendation_plan.policy_version == stored_rec.policy_result.policy_version

    explanation_items = stored_rec.recommendation_plan.explanation.items
    signals = stored_rec.policy_result.signals
    assert len(explanation_items) == len(signals)
    for item, sig in zip(explanation_items, signals):
        assert item.signal_code == sig.code
        assert item.source == sig.source
        assert item.severity == sig.severity
        assert item.summary == sig.summary


def test_recorded_at_relative_to_generated_at():
    gen = datetime.now(timezone.utc)
    # Earlier recorded_at
    rec_earlier = gen - timedelta(seconds=10)
    ctx, res, plan, _ = build_sample_pipeline_record("d-earlier", gen, rec_earlier)
    assert rec_earlier < gen
    assert DecisionAuditRecord(decision_id="d-earlier", recorded_at=rec_earlier, context=ctx, policy_result=res, recommendation_plan=plan).recorded_at == rec_earlier

    # Later recorded_at
    rec_later = gen + timedelta(seconds=10)
    assert DecisionAuditRecord(decision_id="d-later", recorded_at=rec_later, context=ctx, policy_result=res, recommendation_plan=plan).recorded_at == rec_later


def test_detailed_explanation_mismatch_checks():
    now = datetime.now(timezone.utc)
    ctx, res, plan, _ = build_sample_pipeline_record("d-exp-check", now, now)

    # 1. Explanation item source mismatch
    exp_source_diff = DecisionExplanation(
        headline=plan.explanation.headline,
        summary=plan.explanation.summary,
        items=(DecisionExplanationItem(signal_code=res.signals[0].code, source="wrong_source", severity=res.signals[0].severity, summary=res.signals[0].summary),),
    )
    plan_source_diff = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=exp_source_diff,
    )
    with pytest.raises(ValueError, match="source 'wrong_source' does not match signal source"):
        DecisionAuditRecord(decision_id="d1", recorded_at=now, context=ctx, policy_result=res, recommendation_plan=plan_source_diff)

    # 2. Explanation item severity mismatch
    exp_sev_diff = DecisionExplanation(
        headline=plan.explanation.headline,
        summary=plan.explanation.summary,
        items=(DecisionExplanationItem(signal_code=res.signals[0].code, source=res.signals[0].source, severity=DecisionSeverity.CRITICAL, summary=res.signals[0].summary),),
    )
    plan_sev_diff = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=exp_sev_diff,
    )
    with pytest.raises(ValueError, match="does not match signal severity"):
        DecisionAuditRecord(decision_id="d1", recorded_at=now, context=ctx, policy_result=res, recommendation_plan=plan_sev_diff)


    # 3. Explanation item summary mismatch
    exp_sum_diff = DecisionExplanation(
        headline=plan.explanation.headline,
        summary=plan.explanation.summary,
        items=(DecisionExplanationItem(signal_code=res.signals[0].code, source=res.signals[0].source, severity=res.signals[0].severity, summary="wrong summary"),),
    )
    plan_sum_diff = RecommendationPlan(
        generated_at=now,
        action=plan.action,
        severity=plan.severity,
        confidence=plan.confidence,
        policy_version=plan.policy_version,
        recommendations=plan.recommendations,
        explanation=exp_sum_diff,
    )
    with pytest.raises(ValueError, match="summary 'wrong summary' does not match signal summary"):
        DecisionAuditRecord(decision_id="d1", recorded_at=now, context=ctx, policy_result=res, recommendation_plan=plan_sum_diff)


def test_deduplication_triple_duplicates_and_multiple_ids():
    t0 = datetime.now(timezone.utc)
    builder = DecisionHistoryBuilder()

    # 3 duplicates for id1 with different recorded_at
    _, _, _, r1_v1 = build_sample_pipeline_record("id1", t0, t0, rec_score=90.0)
    _, _, _, r1_v2 = build_sample_pipeline_record("id1", t0, t0 + timedelta(seconds=10), rec_score=60.0)
    _, _, _, r1_v3 = build_sample_pipeline_record("id1", t0, t0 + timedelta(seconds=20), rec_score=30.0)

    # 2 duplicates for id2 with identical recorded_at (last in input wins)
    _, _, _, r2_v1 = build_sample_pipeline_record("id2", t0 + timedelta(minutes=5), t0 + timedelta(minutes=5), rec_score=80.0)
    _, _, _, r2_v2 = build_sample_pipeline_record("id2", t0 + timedelta(minutes=5), t0 + timedelta(minutes=5), rec_score=40.0)

    history = builder.build((r1_v1, r2_v1, r1_v3, r1_v2, r2_v2))

    assert len(history.records) == 2
    assert history.records[0].decision_id == "id1"
    assert history.records[0].policy_result.action == DecisionAction.REST  # r1_v3 score 30
    assert history.records[1].decision_id == "id2"
    assert history.records[1].policy_result.action == DecisionAction.REPLACE_WITH_RECOVERY  # r2_v2 score 40


def test_full_pipeline_multi_scenario():
    now = datetime.now(timezone.utc)
    rec_builder = DecisionAuditRecordBuilder()
    hist_builder = DecisionHistoryBuilder()
    policy = DecisionPolicyV2()
    plan_builder = RecommendationPlanBuilder()

    # Scenario 1: PROCEED / LOW
    ctx1 = AthleteDecisionContextBuilder().build(
        generated_at=now,
        recovery=RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=90.0),
        training=TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE"),
        biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0),
        performance=PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE),
    )
    res1 = policy.evaluate(ctx1)
    plan1 = plan_builder.build(res1)
    rec1 = rec_builder.build("scenario-01", now, ctx1, res1, plan1)

    # Scenario 2: REST / CRITICAL with multiple signals
    ctx2 = AthleteDecisionContextBuilder().build(
        generated_at=now + timedelta(hours=1),
        recovery=RecoveryDecisionContext(status=ContextDataStatus.STALE, recovery_score=20.0),
        training=TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="INTERVALS", fatigue_status="high"),
        biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=1, critical_count=1),
        performance=PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE),
    )
    res2 = policy.evaluate(ctx2)
    plan2 = plan_builder.build(res2)
    rec2 = rec_builder.build("scenario-02", now + timedelta(hours=1), ctx2, res2, plan2)

    history = hist_builder.build((rec2, rec1))  # Reverse order input

    assert len(history.records) == 2

    # Preserved order: oldest first (scenario-01) -> newest (scenario-02)
    assert history.records[0].decision_id == "scenario-01"
    assert history.records[0].policy_result.action == DecisionAction.PROCEED
    assert history.records[0].recommendation_plan.recommendations[0].code == "proceed_as_planned"

    assert history.records[1].decision_id == "scenario-02"
    assert history.records[1].policy_result.action == DecisionAction.REST
    assert history.records[1].policy_result.severity == DecisionSeverity.CRITICAL
    assert len(history.records[1].policy_result.signals) == 4
    assert len(history.records[1].recommendation_plan.explanation.items) == 4
