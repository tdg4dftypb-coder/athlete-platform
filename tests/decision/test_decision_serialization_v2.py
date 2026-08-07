from datetime import datetime, timezone
import json
import pytest

from decision import (
    AthleteDecisionContextBuilder,
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    ContextDataStatus,
    DecisionAction,
    DecisionAuditRecordBuilder,
    DecisionAuditRecordSerializer,
    DecisionPolicyV2,
    DecisionSeverity,
    EmptyDecisionAuditRecordProvider,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
    RecommendationCategory,
    RecommendationPlanBuilder,
    RecommendationPriority,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


def build_test_record(action_scenario="proceed") -> tuple[dict[str, object], object]:
    now = datetime.now(timezone.utc)
    if action_scenario == "proceed":
        rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0)
        tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
        bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
        pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)
    else:
        rc = RecoveryDecisionContext(status=ContextDataStatus.STALE, recovery_score=25.0)
        tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="INTERVALS", fatigue_status="high")
        sig = BiomarkerDecisionSignal(canonical_code="FERRITIN", interpretation="LOW", confidence="HIGH")
        bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=1, critical_count=1, signals=(sig,))
        lt1 = PerformanceThresholdSnapshot(name="LT1", status="invalid_curve")
        pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t1", lt1=lt1)

    ctx = AthleteDecisionContextBuilder().build(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)
    policy_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(policy_res)
    record = DecisionAuditRecordBuilder().build("dec-test-01", now, ctx, policy_res, plan)

    serializer = DecisionAuditRecordSerializer()
    serialized = serializer.serialize(record)
    return serialized, record


def test_serializer_full_proceed_and_json_safety():
    serialized, record = build_test_record("proceed")

    # JSON safety check
    json_str = json.dumps(serialized)
    parsed = json.loads(json_str)

    assert parsed["decision_id"] == "dec-test-01"
    assert parsed["context"]["recovery"]["status"] == "available"
    assert parsed["context"]["recovery"]["recovery_score"] == 85.0
    assert parsed["policy_result"]["action"] == "proceed"
    assert parsed["policy_result"]["severity"] == "low"
    assert parsed["policy_result"]["confidence"] == 0.6
    assert parsed["recommendation_plan"]["recommendations"][0]["code"] == "proceed_as_planned"
    assert parsed["recommendation_plan"]["explanation"]["headline"] == "Training can proceed"


def test_serializer_rest_with_multiple_signals():
    serialized, _ = build_test_record("rest")

    assert serialized["policy_result"]["action"] == "rest"
    assert serialized["policy_result"]["severity"] == "critical"
    assert serialized["policy_result"]["confidence"] == 0.95

    signals = serialized["policy_result"]["signals"]
    assert len(signals) == 5
    codes = [s["code"] for s in signals]
    assert codes == ["context_stale", "biomarker_critical", "recovery_very_low", "training_fatigue_high", "performance_threshold_invalid"]


    recs = serialized["recommendation_plan"]["recommendations"]
    rec_codes = [r["code"] for r in recs]
    assert rec_codes == [
        "prioritize_rest",
        "review_critical_laboratory_signals",
        "refresh_stale_data",
        "review_performance_analysis",
    ]



def test_serializer_threshold_snapshots():
    now = datetime.now(timezone.utc)
    lt1 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED", power_watts=200.0, confidence=0.8)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="lac-001", lt1=lt1, lt2=None)

    ctx = AthleteDecisionContextBuilder().build(
        generated_at=now,
        recovery=RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE),
        training=TrainingDecisionContext(status=ContextDataStatus.AVAILABLE),
        biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0),
        performance=pc,
    )
    policy_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(policy_res)
    record = DecisionAuditRecordBuilder().build("d-lt", now, ctx, policy_res, plan)

    serialized = DecisionAuditRecordSerializer().serialize(record)

    perf_json = serialized["context"]["performance"]
    assert perf_json["latest_test_id"] == "lac-001"
    assert perf_json["lt1"]["power_watts"] == 200.0
    assert perf_json["lt1"]["confidence"] == 0.8
    assert perf_json["lt2"] is None


def assert_is_json_safe(val: object) -> None:
    if val is None or isinstance(val, (str, int, float, bool)):
        return
    elif isinstance(val, dict):
        for k, v in val.items():
            assert isinstance(k, str), f"Dict key '{k}' is not a string"
            assert_is_json_safe(v)
    elif isinstance(val, list):
        for item in val:
            assert_is_json_safe(item)
    else:
        pytest.fail(f"Non-JSON-safe type found: {type(val)} (value: {val})")


def test_serializer_keysets_and_json_safety():
    serialized, record = build_test_record("rest")

    # Recursive JSON safety
    assert_is_json_safe(serialized)

    # 1. Root keyset
    assert set(serialized.keys()) == {
        "decision_id",
        "recorded_at",
        "context",
        "policy_result",
        "recommendation_plan",
    }
    assert isinstance(serialized["decision_id"], str)
    assert isinstance(serialized["recorded_at"], str)

    # 2. Context keysets
    ctx = serialized["context"]
    assert set(ctx.keys()) == {
        "generated_at",
        "recovery",
        "training",
        "biomarkers",
        "performance",
    }

    assert set(ctx["recovery"].keys()) == {
        "status",
        "recovery_score",
        "recovery_status",
        "hrv_status",
        "resting_heart_rate_status",
        "sleep_status",
        "generated_at",
    }

    assert set(ctx["training"].keys()) == {
        "status",
        "planned_session_type",
        "planned_duration_minutes",
        "planned_intensity",
        "recent_training_load",
        "fatigue_status",
        "generated_at",
        "plan_id",
        "planned_session_id",
    }

    assert set(ctx["biomarkers"].keys()) == {
        "status",
        "attention_count",
        "critical_count",
        "signals",
        "generated_at",
    }

    assert set(ctx["biomarkers"]["signals"][0].keys()) == {
        "canonical_code",
        "interpretation",
        "confidence",
        "summary",
    }

    assert set(ctx["performance"].keys()) == {
        "status",
        "latest_test_id",
        "latest_test_type",
        "performed_at",
        "lt1",
        "lt2",
    }

    assert set(ctx["performance"]["lt1"].keys()) == {
        "name",
        "status",
        "power_watts",
        "speed_kph",
        "heart_rate_bpm",
        "lactate_mmol_l",
        "confidence",
        "method",
    }

    # 3. Policy Result keysets
    pol = serialized["policy_result"]
    assert set(pol.keys()) == {
        "generated_at",
        "action",
        "severity",
        "signals",
        "confidence",
        "policy_version",
    }
    assert set(pol["signals"][0].keys()) == {
        "code",
        "source",
        "severity",
        "summary",
    }

    # 4. Recommendation Plan keysets
    rec_plan = serialized["recommendation_plan"]
    assert set(rec_plan.keys()) == {
        "generated_at",
        "action",
        "severity",
        "confidence",
        "policy_version",
        "recommendations",
        "explanation",
    }
    assert set(rec_plan["recommendations"][0].keys()) == {
        "code",
        "category",
        "priority",
        "title",
        "description",
        "source_signal_codes",
    }
    assert isinstance(rec_plan["recommendations"][0]["source_signal_codes"], list)

    assert set(rec_plan["explanation"].keys()) == {
        "headline",
        "summary",
        "items",
    }
    assert set(rec_plan["explanation"]["items"][0].keys()) == {
        "signal_code",
        "source",
        "severity",
        "summary",
    }


def test_serializer_privacy_no_internal_metadata():
    serialized, _ = build_test_record("rest")
    json_str = json.dumps(serialized)

    prohibited_privacy_terms = [
        "raw_payload",
        "source_file",
        "filename",
        "document_hash",
        "database_id",
        "observation_id",
        "traceback",
    ]
    for term in prohibited_privacy_terms:
        assert term not in json_str, f"Prohibited privacy term '{term}' found in serialized payload"


def test_serializer_both_lt1_and_lt2():
    now = datetime.now(timezone.utc)
    lt1 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED", power_watts=220.0)
    lt2 = PerformanceThresholdSnapshot(name="LT2", status="DETECTED", power_watts=300.0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t-both", lt1=lt1, lt2=lt2)

    ctx = AthleteDecisionContextBuilder().build(
        generated_at=now,
        recovery=RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE),
        training=TrainingDecisionContext(status=ContextDataStatus.AVAILABLE),
        biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0),
        performance=pc,
    )
    policy_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(policy_res)
    record = DecisionAuditRecordBuilder().build("d-both", now, ctx, policy_res, plan)

    serialized = DecisionAuditRecordSerializer().serialize(record)
    assert serialized["context"]["performance"]["lt1"]["power_watts"] == 220.0
    assert serialized["context"]["performance"]["lt2"]["power_watts"] == 300.0


def test_empty_provider():
    provider = EmptyDecisionAuditRecordProvider()
    assert provider.get_latest_record() is None
