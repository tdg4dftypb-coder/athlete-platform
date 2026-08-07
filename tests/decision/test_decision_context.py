from datetime import datetime, timezone
import pytest

from decision import (
    AthleteDecisionContext,
    BiomarkerDecisionContext,
    BiomarkerDecisionSignal,
    ContextDataStatus,
    PerformanceDecisionContext,
    PerformanceThresholdSnapshot,
    RecoveryDecisionContext,
    TrainingDecisionContext,
)


def test_context_data_status_enum():
    assert ContextDataStatus.AVAILABLE == "available"
    assert ContextDataStatus.PARTIAL == "partial"
    assert ContextDataStatus.UNAVAILABLE == "unavailable"
    assert ContextDataStatus.STALE == "stale"
    assert len(ContextDataStatus) == 4


def test_recovery_decision_context_valid():
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        recovery_score=85.5,
        recovery_status="OPTIMAL",
        hrv_status="HIGH",
        resting_heart_rate_status="NORMAL",
        sleep_status="GOOD",
        generated_at=now,
    )
    assert rc.status == ContextDataStatus.AVAILABLE
    assert rc.recovery_score == 85.5
    assert rc.generated_at == now


def test_recovery_decision_context_score_limits():
    # Boundary 0 and 100
    rc0 = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=0.0)
    assert rc0.recovery_score == 0.0

    rc100 = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=100.0)
    assert rc100.recovery_score == 100.0

    with pytest.raises(ValueError, match="recovery_score must be between 0.0 and 100.0"):
        RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=-0.1)

    with pytest.raises(ValueError, match="recovery_score must be between 0.0 and 100.0"):
        RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=100.1)


def test_training_decision_context_valid():
    tc = TrainingDecisionContext(
        status=ContextDataStatus.PARTIAL,
        planned_session_type="INTERVALS",
        planned_duration_minutes=60,
        planned_intensity="HARD",
        recent_training_load=450.0,
        fatigue_status="MODERATE",
    )
    assert tc.status == ContextDataStatus.PARTIAL
    assert tc.planned_duration_minutes == 60
    assert tc.recent_training_load == 450.0


def test_training_decision_context_invariants():
    tc0 = TrainingDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        planned_duration_minutes=0,
        recent_training_load=0.0,
    )
    assert tc0.planned_duration_minutes == 0
    assert tc0.recent_training_load == 0.0

    with pytest.raises(ValueError, match="planned_duration_minutes must be >= 0"):
        TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_duration_minutes=-1)

    with pytest.raises(ValueError, match="recent_training_load must be >= 0"):
        TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, recent_training_load=-5.0)


def test_biomarker_decision_signal_invariants():
    sig = BiomarkerDecisionSignal(
        canonical_code="FERRITIN",
        interpretation="LOW",
        confidence="HIGH",
        summary="Low iron storage",
    )
    assert sig.canonical_code == "FERRITIN"

    with pytest.raises(ValueError, match="canonical_code must be non-empty"):
        BiomarkerDecisionSignal(canonical_code="", interpretation="LOW", confidence="HIGH")

    with pytest.raises(ValueError, match="interpretation must be non-empty"):
        BiomarkerDecisionSignal(canonical_code="FERRITIN", interpretation="  ", confidence="HIGH")

    with pytest.raises(ValueError, match="confidence must be non-empty"):
        BiomarkerDecisionSignal(canonical_code="FERRITIN", interpretation="LOW", confidence="")


def test_biomarker_decision_context_invariants():
    sig1 = BiomarkerDecisionSignal(canonical_code="FERRITIN", interpretation="LOW", confidence="HIGH")
    sig2 = BiomarkerDecisionSignal(canonical_code="VIT_D", interpretation="DEFICIENT", confidence="HIGH")

    bc = BiomarkerDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        attention_count=2,
        critical_count=1,
        signals=(sig1, sig2),
    )
    assert len(bc.signals) == 2

    # Must be tuple
    with pytest.raises(TypeError, match="signals must be a tuple"):
        BiomarkerDecisionContext(
            status=ContextDataStatus.AVAILABLE,
            attention_count=1,
            critical_count=0,
            signals=[sig1],  # type: ignore
        )

    # Counts
    with pytest.raises(ValueError, match="attention_count must be >= 0"):
        BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=-1, critical_count=0)

    with pytest.raises(ValueError, match="critical_count must be >= 0"):
        BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=-1)

    with pytest.raises(ValueError, match="critical_count must be <= attention_count"):
        BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=1, critical_count=2)

    # Duplicate canonical_code
    with pytest.raises(ValueError, match="Duplicate canonical_code in signals"):
        BiomarkerDecisionContext(
            status=ContextDataStatus.AVAILABLE,
            attention_count=2,
            critical_count=0,
            signals=(sig1, sig1),
        )


def test_performance_threshold_snapshot_invariants():
    pts = PerformanceThresholdSnapshot(
        name="LT1",
        status="DETECTED",
        power_watts=200.0,
        speed_kph=null if False else 15.5,
        heart_rate_bpm=145,
        lactate_mmol_l=2.1,
        confidence=0.9,
        method="fixed_2_mmol",
    )
    assert pts.power_watts == 200.0

    # Boundary confidence
    pts0 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED", confidence=0.0)
    assert pts0.confidence == 0.0
    pts1 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED", confidence=1.0)
    assert pts1.confidence == 1.0

    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        PerformanceThresholdSnapshot(name="LT1", status="DETECTED", confidence=1.1)

    with pytest.raises(ValueError, match="power_watts must be >= 0"):
        PerformanceThresholdSnapshot(name="LT1", status="DETECTED", power_watts=-10.0)

    with pytest.raises(ValueError, match="heart_rate_bpm must be > 0"):
        PerformanceThresholdSnapshot(name="LT1", status="DETECTED", heart_rate_bpm=0)


def test_performance_decision_context_invariants():
    # No test_id -> all other fields must be None
    pc_empty = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    assert pc_empty.latest_test_id is None

    with pytest.raises(ValueError, match="latest_test_type must be None when latest_test_id is None"):
        PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE, latest_test_type="lactate_step_test")

    now = datetime.now(timezone.utc)
    lt1 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED", power_watts=200.0)

    # Valid test with 1 threshold
    pc1 = PerformanceDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        latest_test_id="test-001",
        latest_test_type="lactate_step_test",
        performed_at=now,
        lt1=lt1,
        lt2=None,
    )
    assert pc1.latest_test_id == "test-001"
    assert pc1.lt1 == lt1
    assert pc1.lt2 is None


def test_athlete_decision_context_aggregation():
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score=90.0)
    tc = TrainingDecisionContext(status=ContextDataStatus.PARTIAL, planned_session_type="ENDURANCE")
    bc = BiomarkerDecisionContext(status=ContextDataStatus.UNAVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.STALE, latest_test_id="t-old", performed_at=now)

    adc = AthleteDecisionContext(
        generated_at=now,
        recovery=rc,
        training=tc,
        biomarkers=bc,
        performance=pc,
    )

    assert adc.generated_at == now
    assert adc.recovery.status == ContextDataStatus.AVAILABLE
    assert adc.training.status == ContextDataStatus.PARTIAL
    assert adc.biomarkers.status == ContextDataStatus.UNAVAILABLE
    assert adc.performance.status == ContextDataStatus.STALE


def test_immutability():
    now = datetime.now(timezone.utc)
    rc = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE)
    tc = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE)
    bc = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    adc = AthleteDecisionContext(
        generated_at=now,
        recovery=rc,
        training=tc,
        biomarkers=bc,
        performance=pc,
    )

    with pytest.raises(AttributeError):
        adc.generated_at = now  # type: ignore

    with pytest.raises(AttributeError):
        rc.recovery_score = 50.0  # type: ignore


def test_recovery_decision_context_all_none_and_equality_repr():
    rc1 = RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    assert rc1.recovery_score is None
    assert rc1.recovery_status is None
    assert rc1.hrv_status is None
    assert rc1.resting_heart_rate_status is None
    assert rc1.sleep_status is None
    assert rc1.generated_at is None

    rc2 = RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    assert rc1 == rc2
    assert "RecoveryDecisionContext" in repr(rc1)


def test_training_decision_context_all_none_and_equality_repr():
    tc1 = TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    assert tc1.planned_session_type is None
    assert tc1.planned_duration_minutes is None
    assert tc1.planned_intensity is None
    assert tc1.recent_training_load is None
    assert tc1.fatigue_status is None
    assert tc1.generated_at is None

    tc2 = TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    assert tc1 == tc2
    assert "TrainingDecisionContext" in repr(tc1)


def test_biomarker_decision_signal_summary_none_equality_repr():
    sig1 = BiomarkerDecisionSignal(canonical_code="FERRITIN", interpretation="LOW", confidence="HIGH")
    assert sig1.summary is None

    sig2 = BiomarkerDecisionSignal(canonical_code="FERRITIN", interpretation="LOW", confidence="HIGH")
    assert sig1 == sig2
    assert "BiomarkerDecisionSignal" in repr(sig1)

    # Whitespace only checks
    with pytest.raises(ValueError, match="canonical_code must be non-empty"):
        BiomarkerDecisionSignal(canonical_code="   \t\n  ", interpretation="LOW", confidence="HIGH")


def test_biomarker_decision_context_empty_tuple_order_equality_repr():
    bc1 = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0, signals=())
    assert bc1.signals == ()

    sig1 = BiomarkerDecisionSignal(canonical_code="A", interpretation="LOW", confidence="HIGH")
    sig2 = BiomarkerDecisionSignal(canonical_code="B", interpretation="HIGH", confidence="HIGH")

    bc_order = BiomarkerDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        attention_count=2,
        critical_count=0,
        signals=(sig1, sig2),
    )
    assert bc_order.signals == (sig1, sig2)
    assert bc_order.signals[0].canonical_code == "A"
    assert bc_order.signals[1].canonical_code == "B"

    bc2 = BiomarkerDecisionContext(
        status=ContextDataStatus.AVAILABLE,
        attention_count=2,
        critical_count=0,
        signals=(sig1, sig2),
    )
    assert bc_order == bc2
    assert "BiomarkerDecisionContext" in repr(bc_order)


def test_performance_threshold_snapshot_none_equality_repr():
    pts1 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED")
    assert pts1.power_watts is None
    assert pts1.speed_kph is None
    assert pts1.heart_rate_bpm is None
    assert pts1.lactate_mmol_l is None
    assert pts1.confidence is None
    assert pts1.method is None

    pts2 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED")
    assert pts1 == pts2
    assert "PerformanceThresholdSnapshot" in repr(pts1)

    with pytest.raises(ValueError, match="speed_kph must be >= 0"):
        PerformanceThresholdSnapshot(name="LT1", status="DETECTED", speed_kph=-1.0)

    with pytest.raises(ValueError, match="lactate_mmol_l must be >= 0"):
        PerformanceThresholdSnapshot(name="LT1", status="DETECTED", lactate_mmol_l=-0.5)

    with pytest.raises(ValueError, match="name must be non-empty"):
        PerformanceThresholdSnapshot(name="   ", status="DETECTED")

    with pytest.raises(ValueError, match="status must be non-empty"):
        PerformanceThresholdSnapshot(name="LT1", status="")


def test_performance_decision_context_rules_1_to_9_equality_repr():
    now = datetime.now(timezone.utc)
    lt1 = PerformanceThresholdSnapshot(name="LT1", status="DETECTED", power_watts=200.0)
    lt2 = PerformanceThresholdSnapshot(name="LT2", status="DETECTED", power_watts=300.0)

    # 1. Brak testu (all None)
    pc1 = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    assert pc1.latest_test_id is None
    assert pc1.latest_test_type is None
    assert pc1.performed_at is None
    assert pc1.lt1 is None
    assert pc1.lt2 is None

    # 2. Brak test_id, ale latest_test_type istnieje -> odrzucone
    with pytest.raises(ValueError, match="latest_test_type must be None when latest_test_id is None"):
        PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE, latest_test_type="lactate_step_test")

    # 3. Brak test_id, ale performed_at istnieje -> odrzucone
    with pytest.raises(ValueError, match="performed_at must be None when latest_test_id is None"):
        PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE, performed_at=now)

    # 4. Brak test_id, ale lt1 istnieje -> odrzucone
    with pytest.raises(ValueError, match="lt1 must be None when latest_test_id is None"):
        PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE, lt1=lt1)

    # 5. Brak test_id, ale lt2 istnieje -> odrzucone
    with pytest.raises(ValueError, match="lt2 must be None when latest_test_id is None"):
        PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE, lt2=lt2)

    # 6. Istniejący test bez progów -> dozwolony
    pc6 = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t1")
    assert pc6.latest_test_id == "t1"
    assert pc6.lt1 is None and pc6.lt2 is None

    # 7. Istniejący test tylko z LT1 -> dozwolony
    pc7 = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t1", lt1=lt1)
    assert pc7.lt1 == lt1 and pc7.lt2 is None

    # 8. Istniejący test tylko z LT2 -> dozwolony
    pc8 = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t1", lt2=lt2)
    assert pc8.lt1 is None and pc8.lt2 == lt2

    # 9. Istniejący test z LT1 i LT2 -> dozwolony
    pc9 = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t1", lt1=lt1, lt2=lt2)
    assert pc9.lt1 == lt1 and pc9.lt2 == lt2

    # 10. Equality & repr
    pc9_dup = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE, latest_test_id="t1", lt1=lt1, lt2=lt2)
    assert pc9 == pc9_dup
    assert "PerformanceDecisionContext" in repr(pc9)


def test_athlete_decision_context_all_status_combos_equality_repr():
    now = datetime.now(timezone.utc)
    rc_avail = RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE)
    tc_avail = TrainingDecisionContext(status=ContextDataStatus.AVAILABLE)
    bc_avail = BiomarkerDecisionContext(status=ContextDataStatus.AVAILABLE, attention_count=0, critical_count=0)
    pc_avail = PerformanceDecisionContext(status=ContextDataStatus.AVAILABLE)

    # All AVAILABLE
    adc_avail = AthleteDecisionContext(
        generated_at=now, recovery=rc_avail, training=tc_avail, biomarkers=bc_avail, performance=pc_avail
    )
    assert adc_avail.recovery.status == ContextDataStatus.AVAILABLE

    # All UNAVAILABLE
    rc_unavail = RecoveryDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    tc_unavail = TrainingDecisionContext(status=ContextDataStatus.UNAVAILABLE)
    bc_unavail = BiomarkerDecisionContext(status=ContextDataStatus.UNAVAILABLE, attention_count=0, critical_count=0)
    pc_unavail = PerformanceDecisionContext(status=ContextDataStatus.UNAVAILABLE)

    adc_unavail = AthleteDecisionContext(
        generated_at=now, recovery=rc_unavail, training=tc_unavail, biomarkers=bc_unavail, performance=pc_unavail
    )
    assert adc_unavail.recovery.status == ContextDataStatus.UNAVAILABLE

    # Equality & repr
    adc_avail_dup = AthleteDecisionContext(
        generated_at=now, recovery=rc_avail, training=tc_avail, biomarkers=bc_avail, performance=pc_avail
    )
    assert adc_avail == adc_avail_dup
    assert "AthleteDecisionContext" in repr(adc_avail)


def test_type_integrity_no_implicit_coercion():
    # String "50" passed to score should raise TypeError or fail check, not convert automatically
    with pytest.raises(TypeError):
        RecoveryDecisionContext(status=ContextDataStatus.AVAILABLE, recovery_score="50.0")  # type: ignore

    with pytest.raises(TypeError):
        TrainingDecisionContext(status=ContextDataStatus.AVAILABLE, planned_duration_minutes="60")  # type: ignore


def test_dependency_isolation():
    import importlib
    import sys

    # Reload decision.context in clean check
    mod = importlib.import_module('decision.context')

    # Verify decision.context module file has no prohibited import statements
    import inspect
    source = inspect.getsource(mod)

    prohibited = ["recovery", "biomarkers", "performance_lab", "morning_briefing", "workout", "server", "duckdb"]
    for line in source.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("import ") or line_clean.startswith("from "):
            for p in prohibited:
                assert p not in line_clean.lower(), f"Prohibited import found in decision/context.py: {line_clean}"
