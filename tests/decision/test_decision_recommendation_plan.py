from datetime import datetime, timezone
import pytest

from decision import (
    DecisionAction,
    DecisionExplanation,
    DecisionExplanationItem,
    DecisionPolicyResult,
    DecisionPolicySignal,
    DecisionPolicyV2,
    DecisionRecommendation,
    DecisionSeverity,
    RecommendationCategory,
    RecommendationPlan,
    RecommendationPlanBuilder,
    RecommendationPriority,
)
from decision.context import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    ContextDataStatus,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


def test_enums_and_values():
    assert RecommendationCategory.TRAINING == "training"
    assert RecommendationCategory.RECOVERY == "recovery"
    assert RecommendationCategory.LABORATORY == "laboratory"
    assert RecommendationCategory.DATA_QUALITY == "data_quality"
    assert RecommendationCategory.PERFORMANCE == "performance"

    assert RecommendationPriority.LOW == "low"
    assert RecommendationPriority.MEDIUM == "medium"
    assert RecommendationPriority.HIGH == "high"
    assert RecommendationPriority.CRITICAL == "critical"


def test_decision_recommendation_invariants():
    rec = DecisionRecommendation(
        code="c1",
        category=RecommendationCategory.TRAINING,
        priority=RecommendationPriority.HIGH,
        title="Title",
        description="Desc",
        source_signal_codes=("sig1",),
    )
    assert rec.code == "c1"
    assert rec == DecisionRecommendation(
        code="c1",
        category=RecommendationCategory.TRAINING,
        priority=RecommendationPriority.HIGH,
        title="Title",
        description="Desc",
        source_signal_codes=("sig1",),
    )
    assert "DecisionRecommendation" in repr(rec)

    with pytest.raises(ValueError, match="code must be non-empty"):
        DecisionRecommendation(code="", category=RecommendationCategory.TRAINING, priority=RecommendationPriority.LOW, title="T", description="D", source_signal_codes=("s",))

    with pytest.raises(TypeError, match="source_signal_codes must be tuple"):
        DecisionRecommendation(code="c", category=RecommendationCategory.TRAINING, priority=RecommendationPriority.LOW, title="T", description="D", source_signal_codes=["s"])  # type: ignore

    with pytest.raises(ValueError, match="source_signal_codes cannot be empty"):
        DecisionRecommendation(code="c", category=RecommendationCategory.TRAINING, priority=RecommendationPriority.LOW, title="T", description="D", source_signal_codes=())

    with pytest.raises(ValueError, match="Duplicate source_signal_code"):
        DecisionRecommendation(code="c", category=RecommendationCategory.TRAINING, priority=RecommendationPriority.LOW, title="T", description="D", source_signal_codes=("s1", "s1"))


def test_explanation_item_and_explanation_invariants():
    item1 = DecisionExplanationItem(signal_code="s1", source="src1", severity=DecisionSeverity.HIGH, summary="Sum 1")
    item2 = DecisionExplanationItem(signal_code="s2", source="src2", severity=DecisionSeverity.LOW, summary="Sum 2")

    exp = DecisionExplanation(headline="Headline", summary="Summary", items=(item1, item2))
    assert len(exp.items) == 2
    assert exp == DecisionExplanation(headline="Headline", summary="Summary", items=(item1, item2))
    assert "DecisionExplanation" in repr(exp)

    with pytest.raises(ValueError, match="headline must be non-empty"):
        DecisionExplanation(headline="  ", summary="Sum", items=(item1,))

    with pytest.raises(ValueError, match="items cannot be empty"):
        DecisionExplanation(headline="H", summary="S", items=())

    with pytest.raises(ValueError, match="Duplicate item signal_code"):
        DecisionExplanation(headline="H", summary="S", items=(item1, item1))


def test_recommendation_plan_invariants():
    now = datetime.now(timezone.utc)
    rec = DecisionRecommendation(code="r1", category=RecommendationCategory.TRAINING, priority=RecommendationPriority.LOW, title="T", description="D", source_signal_codes=("s1",))
    item = DecisionExplanationItem(signal_code="s1", source="src", severity=DecisionSeverity.LOW, summary="Sum")
    exp = DecisionExplanation(headline="H", summary="S", items=(item,))

    plan = RecommendationPlan(
        generated_at=now,
        action=DecisionAction.PROCEED,
        severity=DecisionSeverity.LOW,
        confidence=0.6,
        policy_version="2.0",
        recommendations=(rec,),
        explanation=exp,
    )
    assert plan.action == DecisionAction.PROCEED
    assert plan == RecommendationPlan(
        generated_at=now,
        action=DecisionAction.PROCEED,
        severity=DecisionSeverity.LOW,
        confidence=0.6,
        policy_version="2.0",
        recommendations=(rec,),
        explanation=exp,
    )
    assert "RecommendationPlan" in repr(plan)

    with pytest.raises(ValueError, match="recommendations cannot be empty"):
        RecommendationPlan(generated_at=now, action=DecisionAction.PROCEED, severity=DecisionSeverity.LOW, confidence=0.6, policy_version="2.0", recommendations=(), explanation=exp)

    with pytest.raises(ValueError, match="Duplicate recommendation code"):
        RecommendationPlan(generated_at=now, action=DecisionAction.PROCEED, severity=DecisionSeverity.LOW, confidence=0.6, policy_version="2.0", recommendations=(rec, rec), explanation=exp)


def test_action_mappings():
    builder = RecommendationPlanBuilder()
    policy = DecisionPolicyV2()
    now = datetime.now(timezone.utc)

    # 1. PROCEED
    rc_ready = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0)
    tc_plan = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc_clean = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc_clean = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)
    ctx1 = AthleteDecisionContext(generated_at=now, recovery=rc_ready, training=tc_plan, biomarkers=bc_clean, performance=pc_clean)

    res1 = policy.evaluate(ctx1)
    plan1 = builder.build(res1)

    assert plan1.action == DecisionAction.PROCEED
    assert plan1.recommendations[0].code == "proceed_as_planned"
    assert plan1.recommendations[0].category == RecommendationCategory.TRAINING
    assert plan1.recommendations[0].priority == RecommendationPriority.LOW
    assert plan1.recommendations[0].title == "Proceed as planned"
    assert plan1.explanation.headline == "Training can proceed"
    assert plan1.explanation.summary == "The available signals support proceeding with the planned session."

    # 2. REDUCE
    rc_mod = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=65.0)
    ctx2 = AthleteDecisionContext(generated_at=now, recovery=rc_mod, training=tc_plan, biomarkers=bc_clean, performance=pc_clean)
    res2 = policy.evaluate(ctx2)
    plan2 = builder.build(res2)

    assert plan2.action == DecisionAction.REDUCE
    assert plan2.recommendations[0].code == "reduce_training_load"
    assert plan2.recommendations[0].category == RecommendationCategory.TRAINING
    assert plan2.recommendations[0].priority == RecommendationPriority.MEDIUM
    assert plan2.recommendations[0].title == "Reduce training load"
    assert plan2.explanation.headline == "Training load should be reduced"
    assert plan2.explanation.summary == "The available signals support training only with reduced load."

    # 3. REPLACE_WITH_RECOVERY
    rc_low = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=50.0)
    ctx3 = AthleteDecisionContext(generated_at=now, recovery=rc_low, training=tc_plan, biomarkers=bc_clean, performance=pc_clean)
    res3 = policy.evaluate(ctx3)
    plan3 = builder.build(res3)

    assert plan3.action == DecisionAction.REPLACE_WITH_RECOVERY
    assert plan3.recommendations[0].code == "replace_with_recovery"
    assert plan3.recommendations[0].category == RecommendationCategory.RECOVERY
    assert plan3.recommendations[0].priority == RecommendationPriority.HIGH
    assert plan3.recommendations[0].title == "Replace with recovery"
    assert plan3.explanation.headline == "Recovery should replace the planned session"
    assert plan3.explanation.summary == "The available signals support replacing the planned session with recovery."

    # 4. REST
    rc_vlow = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=20.0)
    ctx4 = AthleteDecisionContext(generated_at=now, recovery=rc_vlow, training=tc_plan, biomarkers=bc_clean, performance=pc_clean)
    res4 = policy.evaluate(ctx4)
    plan4 = builder.build(res4)

    assert plan4.action == DecisionAction.REST
    assert plan4.recommendations[0].code == "prioritize_rest"
    assert plan4.recommendations[0].category == RecommendationCategory.RECOVERY
    assert plan4.recommendations[0].priority == RecommendationPriority.CRITICAL
    assert plan4.recommendations[0].title == "Prioritize rest"
    assert plan4.explanation.headline == "Rest is recommended"
    assert plan4.explanation.summary == "The available signals support avoiding the planned session and prioritizing rest."

    # 5. REVIEW
    rc_unavail = RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    tc_unavail = TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    bc_unavail = BiomarkerDecisionContext(status=ContextDataStatus.UNAVAILABLE, attention_count=0, critical_count=0)
    pc_unavail = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    ctx5 = AthleteDecisionContext(generated_at=now, recovery=rc_unavail, training=tc_unavail, biomarkers=bc_unavail, performance=pc_unavail)
    res5 = policy.evaluate(ctx5)
    plan5 = builder.build(res5)

    assert plan5.action == DecisionAction.REVIEW
    assert plan5.recommendations[0].code == "review_before_training"
    assert plan5.recommendations[0].category == RecommendationCategory.DATA_QUALITY
    assert plan5.recommendations[0].priority == RecommendationPriority.HIGH
    assert plan5.recommendations[0].title == "Review before training"
    assert plan5.explanation.headline == "Decision signals require review"
    assert plan5.explanation.summary == "The available signals require review before a training decision is finalized."


def test_additional_recommendations_and_ordering():
    builder = RecommendationPlanBuilder()
    now = datetime.now(timezone.utc)

    # Build context triggering multiple specific signals
    rc_stale = RecoveryDecisionContext(status=ContextDataStatus.STALE, recovery_score=80.0)
    tc_plan = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc_crit = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=1, critical_count=1)
    lt1_invalid = PerformanceThresholdSnapshot(name="LT1", status="invalid_curve")
    pc_invalid = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t1", lt1=lt1_invalid)

    ctx = AthleteDecisionContext(generated_at=now, recovery=rc_stale, training=tc_plan, biomarkers=bc_crit, performance=pc_invalid)
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)
    plan = builder.build(res)

    rec_codes = [r.code for r in plan.recommendations]

    # Order check: main (REST) -> laboratory (biomarker_critical) -> data_quality (context_stale) -> performance (performance_threshold_invalid)
    assert rec_codes == [
        "prioritize_rest",
        "review_critical_laboratory_signals",
        "refresh_stale_data",
        "review_performance_analysis",
    ]

    # Check biomarker_attention extra rec
    bc_att = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=2, critical_count=0)
    ctx_att = AthleteDecisionContext(generated_at=now, recovery=RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0), training=tc_plan, biomarkers=bc_att, performance=PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE))
    res_att = policy.evaluate(ctx_att)
    plan_att = builder.build(res_att)
    assert any(r.code == "review_laboratory_signals" for r in plan_att.recommendations)

    # Check context_all_unavailable extra rec
    rc_u = RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    tc_u = TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    bc_u = BiomarkerDecisionContext(status=ContextDataStatus.UNAVAILABLE, attention_count=0, critical_count=0)
    pc_u = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    ctx_all_u = AthleteDecisionContext(generated_at=now, recovery=rc_u, training=tc_u, biomarkers=bc_u, performance=pc_u)
    res_all_u = policy.evaluate(ctx_all_u)
    plan_all_u = builder.build(res_all_u)
    assert any(r.code == "restore_decision_data" for r in plan_all_u.recommendations)

    # Signals for recovery, fatigue, missing plan do NOT create extra recommendations
    rc_mod = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=65.0)
    tc_fatigue = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type=None, fatigue_status="high")
    bc_clean = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    ctx_no_extra = AthleteDecisionContext(generated_at=now, recovery=rc_mod, training=tc_fatigue, biomarkers=bc_clean, performance=PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE))
    res_no_extra = policy.evaluate(ctx_no_extra)
    plan_no_extra = builder.build(res_no_extra)
    assert len(plan_no_extra.recommendations) == 1



def test_explanation_mapping():
    builder = RecommendationPlanBuilder()
    policy = DecisionPolicyV2()
    now = datetime.now(timezone.utc)

    ctx = AthleteDecisionContext(
        generated_at=now,
        recovery=RecoveryDecisionContext(status=ContextDataStatus.STALE, recovery_score=35.0),
        training=TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="INTERVALS", fatigue_status="high"),
        biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=1, critical_count=1),
        performance=PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE),
    )
    res = policy.evaluate(ctx)
    plan = builder.build(res)

    exp_items = plan.explanation.items
    assert len(exp_items) == len(res.signals)
    for item, sig in zip(exp_items, res.signals):
        assert item.signal_code == sig.code
        assert item.source == sig.source
        assert item.severity == sig.severity
        assert item.summary == sig.summary


def test_stateless_and_idempotent_builder():
    builder = RecommendationPlanBuilder()
    policy = DecisionPolicyV2()
    now = datetime.now(timezone.utc)

    ctx = AthleteDecisionContext(
        generated_at=now,
        recovery=RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0),
        training=TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE"),
        biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0),
        performance=PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE),
    )
    res = policy.evaluate(ctx)

    plan1 = builder.build(res)
    plan2 = builder.build(res)

    assert plan1 == plan2
    assert plan1.generated_at == res.generated_at
    assert plan1.action == res.action
    assert plan1.severity == res.severity
    assert plan1.confidence == res.confidence
    assert plan1.policy_version == res.policy_version


def test_architecture_dependency_isolation():
    import importlib
    import inspect

    mod = importlib.import_module('decision.recommendation_plan')
    source = inspect.getsource(mod)

    prohibited = ["recovery", "biomarkers", "performance_lab", "morning_briefing", "workout", "server", "duckdb"]
    for line in source.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("import ") or line_clean.startswith("from "):
            for p in prohibited:
                assert p not in line_clean, f"Prohibited import found in recommendation_plan.py: {line_clean}"
