from datetime import datetime, timezone
import pytest

from decision import (
    AthleteDecisionContextBuilder,
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    ContextDataStatus,
    DecisionAuditRecordBuilder,
    DecisionAuditRecordCodec,
    DecisionAuditRecordDataError,
    DecisionPolicyV2,
    PerformanceDecisionContext,
    RecommendationPlanBuilder,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


def build_sample_record(decision_id="rec-01", gen_at=None):
    gen_at = gen_at or datetime.now(timezone.utc)
    rec_at = gen_at

    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=85.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        attention_count=1,
        critical_count=0,
        signals=(BiomarkerDecisionSignal("FERRITIN", "ATTENTION", "HIGH", "Low ferritin"),),
    )
    pc = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    ctx = AthleteDecisionContextBuilder().build(gen_at, rc, tc, bc, pc)
    pol_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(pol_res)
    return DecisionAuditRecordBuilder().build(decision_id, rec_at, ctx, pol_res, plan)


def test_codec_round_trip():
    codec = DecisionAuditRecordCodec()
    rec1 = build_sample_record("codec-01")

    encoded = codec.encode(rec1)
    assert isinstance(encoded, str)
    assert "codec-01" in encoded

    decoded = codec.decode(encoded)
    assert decoded == rec1
    assert decoded.decision_id == rec1.decision_id
    assert decoded.context.generated_at == rec1.context.generated_at


def test_codec_encode_is_canonical():
    codec = DecisionAuditRecordCodec()
    rec1 = build_sample_record("codec-canonical")

    encoded1 = codec.encode(rec1)
    encoded2 = codec.encode(rec1)
    assert encoded1 == encoded2


def test_codec_decode_corrupted_payload_raises_data_error():
    codec = DecisionAuditRecordCodec()

    # Invalid JSON
    with pytest.raises(DecisionAuditRecordDataError, match="Invalid JSON"):
        codec.decode("not a json")

    # Root not object
    with pytest.raises(DecisionAuditRecordDataError, match="Payload root must be an object"):
        codec.decode("[1, 2, 3]")

    # Missing fields / invalid structure
    with pytest.raises(DecisionAuditRecordDataError, match="Corrupted or inconsistent"):
        codec.decode('{"decision_id": "d1"}')


def test_codec_performance_thresholds_round_trip():
    from decision.context import PerformanceThresholdSnapshot
    codec = DecisionAuditRecordCodec()
    gen_at = datetime.now(timezone.utc)

    lt1 = PerformanceThresholdSnapshot("LT1", "detected", 200.0, 30.0, 150, 2.0, 0.9, "fixed_2_mmol")
    lt2 = PerformanceThresholdSnapshot("LT2", "detected", 280.0, 40.0, 175, 4.0, 0.95, "fixed_4_mmol")
    pc = PerformanceDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        latest_test_id="test-perf-01",
        latest_test_type="lactate_step_test",
        performed_at=gen_at,
        lt1=lt1,
        lt2=lt2,
    )
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=90.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_session_type="INTERVALS")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)

    ctx = AthleteDecisionContextBuilder().build(gen_at, rc, tc, bc, pc)
    pol_res = DecisionPolicyV2().evaluate(ctx)
    plan = RecommendationPlanBuilder().build(pol_res)
    rec = DecisionAuditRecordBuilder().build("perf-rec-01", gen_at, ctx, pol_res, plan)

    encoded = codec.encode(rec)
    decoded = codec.decode(encoded)

    assert decoded == rec
    assert decoded.context.performance.lt1 == lt1
    assert decoded.context.performance.lt2 == lt2
