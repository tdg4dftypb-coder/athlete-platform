from datetime import datetime, timezone
import pytest

from decision import (
    AthleteDecisionContext,
    AthleteDecisionContextBuilder,
    AthleteDecisionContextProvider,
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    ContextDataStatus,
    EmptyAthleteDecisionContextProvider,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


def test_builder_full_context():
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=88.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_duration_minutes=90)
    sig = BiomarkerDecisionSignal(canonical_code="FERRITIN", interpretation="LOW", confidence="HIGH")
    bc = BiomarkerDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        attention_count=1,
        critical_count=0,
        signals=(sig,),
    )
    lt1 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED", power_watts=210.0)
    pc = PerformanceDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        latest_test_id="test-101",
        latest_test_type="lactate_step_test",
        performed_at=now,
        lt1=lt1,
    )

    builder = AthleteDecisionContextBuilder()
    adc = builder.build(
        generated_at=now,
        recovery=rc,
        training=tc,
        biomarkers=bc,
        performance=pc,
    )

    assert isinstance(adc, AthleteDecisionContext)
    assert adc.generated_at == now
    assert adc.recovery == rc
    assert adc.training == tc
    assert adc.biomarkers == bc
    assert adc.performance == pc


def test_builder_all_unavailable_and_mixed_statuses():
    now = datetime.now(timezone.utc)
    rc_unavail = RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    tc_unavail = TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    bc_unavail = BiomarkerDecisionContext(status=ContextDataStatus.UNAVAILABLE, attention_count=0, critical_count=0)
    pc_unavail = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)

    builder = AthleteDecisionContextBuilder()
    adc_unavail = builder.build(
        generated_at=now,
        recovery=rc_unavail,
        training=tc_unavail,
        biomarkers=bc_unavail,
        performance=pc_unavail,
    )

    assert adc_unavail.recovery.status == ContextDataStatus.UNAVAILABLE
    assert adc_unavail.training.status == ContextDataStatus.UNAVAILABLE
    assert adc_unavail.biomarkers.status == ContextDataStatus.UNAVAILABLE
    assert adc_unavail.performance.status == ContextDataStatus.UNAVAILABLE

    # Mixed statuses
    rc_partial = RecoveryDecisionContext(status=ContextDataStatus.PARTIAL)
    pc_stale = PerformanceDecisionContext(status=ContextDataStatus.STALE, latest_test_id="t-old", performed_at=now)

    adc_mixed = builder.build(
        generated_at=now,
        recovery=rc_partial,
        training=tc_unavail,
        biomarkers=bc_unavail,
        performance=pc_stale,
    )

    assert adc_mixed.recovery.status == ContextDataStatus.PARTIAL
    assert adc_mixed.performance.status == ContextDataStatus.STALE


def test_builder_immutability_equality_repr():
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE)
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    builder = AthleteDecisionContextBuilder()
    adc1 = builder.build(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)
    adc2 = builder.build(generated_at=now, recovery=rc, training=tc, biomarkers=bc, performance=pc)

    assert adc1 == adc2
    assert "AthleteDecisionContext" in repr(adc1)

    with pytest.raises(AttributeError):
        adc1.generated_at = now  # type: ignore


def test_builder_invalid_timestamp():
    builder = AthleteDecisionContextBuilder()
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE)
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    with pytest.raises(TypeError, match="generated_at must be a datetime"):
        builder.build(generated_at="2026-08-01", recovery=rc, training=tc, biomarkers=bc, performance=pc)  # type: ignore


def test_empty_provider():
    provider = EmptyAthleteDecisionContextProvider()
    now = datetime.now(timezone.utc)

    adc = provider.build_context(generated_at=now)

    assert isinstance(adc, AthleteDecisionContext)
    assert adc.generated_at == now
    assert adc.recovery.status == ContextDataStatus.UNAVAILABLE
    assert adc.recovery.recovery_score is None
    assert adc.training.status == ContextDataStatus.UNAVAILABLE
    assert adc.training.planned_duration_minutes is None
    assert adc.biomarkers.status == ContextDataStatus.UNAVAILABLE
    assert adc.biomarkers.attention_count == 0
    assert adc.biomarkers.signals == ()
    assert adc.performance.status == ContextDataStatus.UNAVAILABLE
    assert adc.performance.latest_test_id is None

    with pytest.raises(TypeError, match="generated_at must be a datetime"):
        provider.build_context(generated_at="invalid")  # type: ignore


def test_provider_protocol():
    class CustomProvider:
        def build_context(self, generated_at: datetime) -> AthleteDecisionContext:
            builder = AthleteDecisionContextBuilder()
            return builder.build(
                generated_at=generated_at,
                recovery=RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE),
                training=TrainingDecisionContext(status=ContextDataStatus.AVAILABLE),
                biomarkers=BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0),
                performance=PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE),
            )

    provider: AthleteDecisionContextProvider = CustomProvider()
    now = datetime.now(timezone.utc)
    res = provider.build_context(now)
    assert res.recovery.status == ContextDataStatus.AVAILABLE


def test_architecture_dependency_isolation():
    import importlib
    import inspect

    for mod_name in ['decision.context_builder', 'decision.context_provider']:
        mod = importlib.import_module(mod_name)
        source = inspect.getsource(mod)

        prohibited = ["recovery", "biomarkers", "performance_lab", "morning_briefing", "workout", "server", "duckdb"]
        for line in source.splitlines():
            line_clean = line.strip()
            if line_clean.startswith("import ") or line_clean.startswith("from "):
                for p in prohibited:
                    assert p not in line_clean.lower(), f"Prohibited import found in {mod_name}: {line_clean}"
