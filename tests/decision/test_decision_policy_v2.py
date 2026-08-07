from datetime import datetime, timezone
import pytest

from decision import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    ContextDataStatus,
    DecisionAction,
    DecisionPolicyResult,
    DecisionPolicySignal,
    DecisionPolicyV2,
    DecisionSeverity,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


def test_enums_and_values():
    assert DecisionAction.PROCEED == "proceed"
    assert DecisionAction.REDUCE == "reduce"
    assert DecisionAction.REPLACE_WITH_RECOVERY == "replace_with_recovery"
    assert DecisionAction.REST == "rest"
    assert DecisionAction.REVIEW == "review"

    assert DecisionSeverity.LOW == "low"
    assert DecisionSeverity.MEDIUM == "medium"
    assert DecisionSeverity.HIGH == "high"
    assert DecisionSeverity.CRITICAL == "critical"


def test_decision_policy_signal_invariants():
    sig = DecisionPolicySignal(
        code="code1",
        source="src1",
        severity=DecisionSeverity.HIGH,
        summary="Summary test",
    )
    assert sig.code == "code1"
    assert sig == DecisionPolicySignal(
        code="code1",
        source="src1",
        severity=DecisionSeverity.HIGH,
        summary="Summary test",
    )
    assert "DecisionPolicySignal" in repr(sig)

    with pytest.raises(ValueError, match="code must be non-empty"):
        DecisionPolicySignal(code="  ", source="src", severity=DecisionSeverity.LOW, summary="sum")

    with pytest.raises(ValueError, match="source must be non-empty"):
        DecisionPolicySignal(code="c", source="", severity=DecisionSeverity.LOW, summary="sum")

    with pytest.raises(ValueError, match="summary must be non-empty"):
        DecisionPolicySignal(code="c", source="src", severity=DecisionSeverity.LOW, summary="")


def test_decision_policy_result_invariants():
    now = datetime.now(timezone.utc)
    sig = DecisionPolicySignal(code="c1", source="s1", severity=DecisionSeverity.LOW, summary="sum")
    res = DecisionPolicyResult(
        generated_at=now,
        action=DecisionAction.PROCEED,
        severity=DecisionSeverity.LOW,
        signals=(sig,),
        confidence=0.6,
        policy_version="2.0",
    )
    assert res.action == DecisionAction.PROCEED
    assert res == DecisionPolicyResult(
        generated_at=now,
        action=DecisionAction.PROCEED,
        severity=DecisionSeverity.LOW,
        signals=(sig,),
        confidence=0.6,
        policy_version="2.0",
    )
    assert "DecisionPolicyResult" in repr(res)

    with pytest.raises(TypeError, match="signals must be tuple"):
        DecisionPolicyResult(
            generated_at=now,
            action=DecisionAction.PROCEED,
            severity=DecisionSeverity.LOW,
            signals=[sig],  # type: ignore
            confidence=0.6,
            policy_version="2.0",
        )

    with pytest.raises(ValueError, match="Duplicate signal code"):
        DecisionPolicyResult(
            generated_at=now,
            action=DecisionAction.PROCEED,
            severity=DecisionSeverity.LOW,
            signals=(sig, sig),
            confidence=0.6,
            policy_version="2.0",
        )

    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        DecisionPolicyResult(
            generated_at=now,
            action=DecisionAction.PROCEED,
            severity=DecisionSeverity.LOW,
            signals=(sig,),
            confidence=1.5,
            policy_version="2.0",
        )


def build_test_context(
    rec_status=ContextDataStatus.AVAILABLE,
    rec_score=80.0,
    tr_status=ContextDataStatus.AVAILABLE,
    tr_type="ENDURANCE",
    tr_fatigue=None,
    bio_status=ContextDataStatus.AVAILABLE,
    bio_critical=0,
    bio_attention=None,
    perf_status=ContextDataStatus.AVAILABLE,
    lt1_status="DETECTED",
    lt2_status="DETECTED",
):
    now = datetime.now(timezone.utc)
    if bio_attention is None:
        bio_attention = max(bio_critical, 0)

    rc = RecoveryDecisionContext(status=rec_status, recovery_score=rec_score)
    tc = TrainingDecisionContext(status=tr_status, planned_session_type=tr_type, fatigue_status=tr_fatigue)
    bc = BiomarkerDecisionContext(status=bio_status, attention_count=bio_attention, critical_count=bio_critical)
    lt1 = PerformanceThresholdSnapshot(name="LT1", status=lt1_status) if perf_status == ContextDataStatus.AVAILABLE else None
    lt2 = PerformanceThresholdSnapshot(name="LT2", status=lt2_status) if perf_status == ContextDataStatus.AVAILABLE else None
    pc = PerformanceDecisionContext(status=perf_status, latest_test_id="t1" if perf_status == ContextDataStatus.AVAILABLE else None, lt1=lt1, lt2=lt2)
    return AthleteDecisionContext(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)



def test_rule_1_all_unavailable():
    ctx = build_test_context(
        rec_status=ContextDataStatus.UNAVAILABLE,
        rec_score=None,
        tr_status=ContextDataStatus.UNAVAILABLE,
        tr_type=None,
        bio_status=ContextDataStatus.UNAVAILABLE,
        perf_status=ContextDataStatus.UNAVAILABLE,
    )
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.REVIEW
    assert res.severity == DecisionSeverity.HIGH
    assert res.confidence == 0.85
    assert len(res.signals) == 1
    assert res.signals[0].code == "context_all_unavailable"


def test_rule_2_stale_data():
    ctx = build_test_context(rec_status=ContextDataStatus.STALE, rec_score=80.0)
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.REVIEW
    assert any(s.code == "context_stale" for s in res.signals)


def test_rule_3_biomarker_critical():
    ctx = build_test_context(bio_critical=1, bio_attention=1)
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.REST
    assert res.severity == DecisionSeverity.CRITICAL
    assert res.confidence == 0.95
    assert any(s.code == "biomarker_critical" for s in res.signals)


def test_rule_4_biomarker_attention():
    ctx = build_test_context(bio_critical=0, bio_attention=2)
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.REVIEW
    assert any(s.code == "biomarker_attention" for s in res.signals)


def test_rule_5_to_8_recovery_ranges():
    policy = DecisionPolicyV2()

    # Score < 40 -> REST
    res0 = policy.evaluate(build_test_context(rec_score=0.0))
    assert res0.action == DecisionAction.REST
    assert any(s.code == "recovery_very_low" for s in res0.signals)

    res39 = policy.evaluate(build_test_context(rec_score=39.9))
    assert res39.action == DecisionAction.REST

    # 40 <= score < 60 -> REPLACE_WITH_RECOVERY
    res40 = policy.evaluate(build_test_context(rec_score=40.0))
    assert res40.action == DecisionAction.REPLACE_WITH_RECOVERY
    assert any(s.code == "recovery_low" for s in res40.signals)

    res59 = policy.evaluate(build_test_context(rec_score=59.9))
    assert res59.action == DecisionAction.REPLACE_WITH_RECOVERY

    # 60 <= score < 75 -> REDUCE
    res60 = policy.evaluate(build_test_context(rec_score=60.0))
    assert res60.action == DecisionAction.REDUCE
    assert any(s.code == "recovery_moderate" for s in res60.signals)

    res74 = policy.evaluate(build_test_context(rec_score=74.9))
    assert res74.action == DecisionAction.REDUCE

    # >= 75 -> PROCEED
    res75 = policy.evaluate(build_test_context(rec_score=75.0))
    assert res75.action == DecisionAction.PROCEED
    assert any(s.code == "recovery_ready" for s in res75.signals)

    res100 = policy.evaluate(build_test_context(rec_score=100.0))
    assert res100.action == DecisionAction.PROCEED


def test_rule_9_training_fatigue_high():
    ctx = build_test_context(tr_fatigue="high", rec_score=80.0)
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.REDUCE
    assert any(s.code == "training_fatigue_high" for s in res.signals)

    # Non-exact 'high' string does not trigger
    ctx_other = build_test_context(tr_fatigue="HIGH_FATIGUE", rec_score=80.0)
    res_other = policy.evaluate(ctx_other)
    assert not any(s.code == "training_fatigue_high" for s in res_other.signals)


def test_rule_10_training_plan_missing():
    ctx = build_test_context(tr_type=None, tr_status=ContextDataStatus.AVAILABLE, rec_score=80.0)
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.REVIEW
    assert any(s.code == "training_plan_missing" for s in res.signals)

    # UNAVAILABLE training status without plan does NOT trigger training_plan_missing
    ctx_unavail = build_test_context(tr_type=None, tr_status=ContextDataStatus.UNAVAILABLE, rec_score=80.0)
    res_unavail = policy.evaluate(ctx_unavail)
    assert not any(s.code == "training_plan_missing" for s in res_unavail.signals)


def test_performance_invalid_threshold():
    ctx = build_test_context(lt1_status="invalid_curve")
    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.REVIEW
    assert any(s.code == "performance_threshold_invalid" for s in res.signals)

    # Both invalid -> single performance signal
    ctx_both = build_test_context(lt1_status="invalid_curve", lt2_status="invalid_curve")
    res_both = policy.evaluate(ctx_both)
    perf_signals = [s for s in res_both.signals if s.code == "performance_threshold_invalid"]
    assert len(perf_signals) == 1


def test_fallback_no_actionable_signal():
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=None)
    tc = TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE, planned_session_type=None)
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    ctx = AthleteDecisionContext(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)

    policy = DecisionPolicyV2()
    res = policy.evaluate(ctx)

    assert res.action == DecisionAction.PROCEED
    assert res.severity == DecisionSeverity.LOW
    assert len(res.signals) == 1
    assert res.signals[0].code == "context_no_actionable_signal"


def test_conflict_resolution_and_signal_ordering():
    policy = DecisionPolicyV2()

    # Recovery ready + fatigue high -> REDUCE (prio 2 vs 1)
    res1 = policy.evaluate(build_test_context(rec_score=80.0, tr_fatigue="high"))
    assert res1.action == DecisionAction.REDUCE

    # Recovery low + biomarker attention -> REVIEW (prio 4 vs 3)
    res2 = policy.evaluate(build_test_context(rec_score=50.0, bio_attention=1))
    assert res2.action == DecisionAction.REVIEW

    # Recovery very low + biomarker attention -> REST (prio 5 vs 4)
    res3 = policy.evaluate(build_test_context(rec_score=20.0, bio_attention=1))
    assert res3.action == DecisionAction.REST

    # Signal order check: context -> biomarkers -> recovery -> training -> performance
    ctx = build_test_context(
        rec_status=ContextDataStatus.STALE,
        rec_score=30.0,
        bio_critical=1,
        tr_fatigue="high",
        lt1_status="invalid_curve",
    )
    res_order = policy.evaluate(ctx)
    codes = [s.code for s in res_order.signals]
    assert codes == [
        "context_stale",
        "biomarker_critical",
        "recovery_very_low",
        "training_fatigue_high",
        "performance_threshold_invalid",
    ]


def test_confidence_mapping():
    policy = DecisionPolicyV2()

    # CRITICAL -> 0.95
    res_crit = policy.evaluate(build_test_context(bio_critical=1))
    assert res_crit.confidence == 0.95

    # HIGH -> 0.85
    res_high = policy.evaluate(build_test_context(rec_score=50.0))
    assert res_high.confidence == 0.85

    # MEDIUM -> 0.70
    res_med = policy.evaluate(build_test_context(rec_score=65.0))
    assert res_med.confidence == 0.70

    # LOW -> 0.60
    res_low = policy.evaluate(build_test_context(rec_score=80.0))
    assert res_low.confidence == 0.60


def test_stateless_and_deterministic_behavior():
    now = datetime.now(timezone.utc)
    ctx = build_test_context(rec_score=85.0)
    policy = DecisionPolicyV2()

    res1 = policy.evaluate(ctx)
    res2 = policy.evaluate(ctx)

    assert res1 == res2
    assert res1.generated_at == ctx.generated_at
    assert res1.policy_version == "2.0"


def test_architecture_dependency_isolation():
    import importlib
    import inspect

    mod = importlib.import_module('decision.policy_v2')
    source = inspect.getsource(mod)

    prohibited = ["recovery", "biomarkers", "performance_lab", "morning_briefing", "workout", "server", "duckdb", "DecisionEngine"]
    for line in source.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("import ") or line_clean.startswith("from "):
            for p in prohibited:
                assert p not in line_clean, f"Prohibited import found in policy_v2.py: {line_clean}"
