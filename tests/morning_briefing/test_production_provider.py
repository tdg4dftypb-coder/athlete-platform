from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from morning_briefing.input_models import (
    BiomarkerBriefingInput,
    MorningBriefingInput,
    RecoveryBriefingInput,
    TrainingBriefingInput,
)
from morning_briefing.production_provider import ProductionMorningBriefingInputProvider
from morning_briefing.provider import MorningBriefingInputError, MorningBriefingInputProvider


def test_implements_protocol():
    mock_use_case = MagicMock()
    provider = ProductionMorningBriefingInputProvider(morning_coach_use_case=mock_use_case)
    assert isinstance(provider, MorningBriefingInputProvider)


def test_biomarker_available_count_semantics():
    """Verify available_count equals canonical biomarker summaries count, NOT raw observation count."""
    mock_use_case = MagicMock()
    mock_coach_result = MagicMock()
    mock_coach_result.athlete_state.context.today.date = date(2026, 8, 7)
    mock_use_case.run.return_value = mock_coach_result

    mock_bio_builder = MagicMock()
    mock_dashboard = MagicMock()
    # 10 raw historical observations, but only 1 canonical biomarker summary in 1 category
    mock_dashboard.verified_observations = 10

    mock_bio_summary = MagicMock()
    mock_category = MagicMock()
    mock_category.biomarkers = (mock_bio_summary,)
    mock_category.attention_count = 0
    mock_dashboard.categories = (mock_category,)

    mock_bio_builder.build.return_value = mock_dashboard

    fixed_time = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    provider = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=mock_use_case,
        biomarkers_dashboard_builder=mock_bio_builder,
        clock=lambda: fixed_time,
    )

    inp = provider.get_input()

    assert inp.biomarkers is not None
    # available_count must be 1 (canonical summaries count), NOT 10 (raw observations)
    assert inp.biomarkers.available_count == 1
    assert inp.biomarkers.attention_count == 0
    # Documented staleness semantics
    assert inp.biomarkers.is_stale is False


def test_recovery_freshness_semantics():
    """Verify is_stale is False when health snapshot date matches generated_at date, and True when different."""
    mock_use_case = MagicMock()
    mock_coach_result = MagicMock()
    mock_coach_result.athlete_state.recovery.score = 80
    mock_coach_result.athlete_state.recovery.status = "🟢 DOBRA"
    mock_coach_result.athlete_state.recovery.reasons = []
    mock_use_case.run.return_value = mock_coach_result

    # 1. Fresh date (same day)
    mock_coach_result.athlete_state.context.today.date = date(2026, 8, 7)
    fixed_time = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)

    provider = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=mock_use_case,
        clock=lambda: fixed_time,
    )
    inp1 = provider.get_input()
    assert inp1.recovery is not None
    assert inp1.recovery.is_stale is False

    # 2. Stale date (previous day)
    mock_coach_result.athlete_state.context.today.date = date(2026, 8, 6)
    inp2 = provider.get_input()
    assert inp2.recovery is not None
    assert inp2.recovery.is_stale is True


def test_tight_error_boundary_source_exceptions():
    """Verify source exceptions raise MorningBriefingInputError, while mapping errors raise unmasked exceptions."""
    # Source 1 exception
    mock_use_case_fail = MagicMock()
    mock_use_case_fail.run.side_effect = RuntimeError("Database connection lost")
    provider1 = ProductionMorningBriefingInputProvider(morning_coach_use_case=mock_use_case_fail)
    with pytest.raises(MorningBriefingInputError, match="Failed to load MorningCoach data source"):
        provider1.get_input()

    # Source 2 exception
    mock_use_case_ok = MagicMock()
    mock_use_case_ok.run.return_value = MagicMock()
    mock_bio_fail = MagicMock()
    mock_bio_fail.build.side_effect = ValueError("Corrupted schema")
    provider2 = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=mock_use_case_ok,
        biomarkers_dashboard_builder=mock_bio_fail,
    )
    with pytest.raises(MorningBriefingInputError, match="Failed to load Biomarkers data source"):
        provider2.get_input()


def test_architectural_rule_one_get_input_one_snapshot():
    """Architectural Test enforcing: ONE get_input() = ONE MorningCoach snapshot + ONE Biomarkers snapshot."""
    mock_use_case = MagicMock()
    mock_use_case.run.return_value = MagicMock()
    mock_bio_builder = MagicMock()
    mock_bio_builder.build.return_value = MagicMock(categories=())

    provider = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=mock_use_case,
        biomarkers_dashboard_builder=mock_bio_builder,
    )

    provider.get_input()

    assert mock_use_case.run.call_count == 1
    assert mock_bio_builder.build.call_count == 1


def test_missing_optional_data_handles_partial_input():
    mock_use_case = MagicMock()
    mock_coach_result = MagicMock()
    mock_coach_result.athlete_state.recovery = None
    mock_coach_result.planned_workout = None
    mock_use_case.run.return_value = mock_coach_result

    provider = ProductionMorningBriefingInputProvider(morning_coach_use_case=mock_use_case)
    inp = provider.get_input()

    assert inp.recovery is None
    assert inp.training.is_available is False
    assert inp.biomarkers is None


def test_recovery_metric_statuses_mapped_to_input():
    mock_use_case = MagicMock()
    mock_coach_result = MagicMock()
    mock_coach_result.athlete_state.context.today.date = date(2026, 8, 7)
    mock_coach_result.athlete_state.recovery.score = 90
    mock_coach_result.athlete_state.recovery.status = "🟢 DOBRA"
    mock_coach_result.athlete_state.recovery.reasons = []

    mock_hrv = MagicMock()
    mock_hrv.status.value = "supportive"
    mock_rhr = MagicMock()
    mock_rhr.status.value = "neutral"
    mock_sleep = MagicMock()
    mock_sleep.status.value = "caution"

    mock_coach_result.athlete_state.recovery.hrv = mock_hrv
    mock_coach_result.athlete_state.recovery.resting_hr = mock_rhr
    mock_coach_result.athlete_state.recovery.sleep = mock_sleep

    mock_use_case.run.return_value = mock_coach_result

    fixed_time = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    provider = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=mock_use_case,
        clock=lambda: fixed_time,
    )

    inp = provider.get_input()

    assert inp.recovery is not None
    assert inp.recovery.hrv_status == "supportive"
    assert inp.recovery.resting_heart_rate_status == "neutral"
    assert inp.recovery.sleep_status == "caution"


def test_training_enrichment_mapped_to_input():
    mock_use_case = MagicMock()
    mock_coach_result = MagicMock()
    mock_coach_result.athlete_state.context.today.date = date(2026, 8, 7)

    # 1. Decision recommendation -> session_type="tempo", intensity="moderate"
    mock_decision_res = MagicMock()
    mock_decision_res.decision.recommendation.value = "tempo"
    mock_decision_res.decision.intensity = "moderate"
    mock_coach_result.decision = mock_decision_res

    # 2. Performance weekly load -> 450.0 TSS
    mock_coach_result.athlete_state.performance.weekly.total_tss = 450.0

    # 3. Assessment fatigue status -> FatigueStatus.HIGH
    mock_coach_result.athlete_assessment.fatigue_status.value = "high"

    # 4. Planned workout
    mock_pw = MagicMock()
    mock_pw.name = "Sweet Spot Builder"
    mock_pw.sport = "cycling"
    mock_pw.target_tss = 80
    mock_pw.estimated_duration = 75
    mock_coach_result.planned_workout = mock_pw

    mock_use_case.run.return_value = mock_coach_result

    provider = ProductionMorningBriefingInputProvider(morning_coach_use_case=mock_use_case)
    inp = provider.get_input()

    assert inp.training is not None
    assert inp.training.title == "Sweet Spot Builder"
    assert inp.training.session_type == "tempo"  # Canonical value, NOT presentation title "sweet spot builder"
    assert inp.training.intensity == "moderate"
    assert inp.training.recent_training_load == 450.0
    assert inp.training.fatigue_status == "high"


def test_biomarker_enrichment_attention_vs_critical_and_signals():
    mock_use_case = MagicMock()

    # Biomarker A: Ferritin (flag L, no critical flag) -> attention=1, critical=0
    bio_a = MagicMock()
    bio_a.canonical_code = "ferritin"
    bio_a.laboratory_flag = "L"
    bio_a.laboratory_provided_critical_flag = None
    bio_a.data_quality = "high"

    # Biomarker B: CRP (flag H, critical flag CRITICAL) -> attention=1, critical=1
    bio_b = MagicMock()
    bio_b.canonical_code = "crp"
    bio_b.laboratory_flag = "H"
    bio_b.laboratory_provided_critical_flag = "CRITICAL"
    bio_b.data_quality = "medium"

    # Biomarker C: Vitamin D (no flags) -> attention=0, critical=0
    bio_c = MagicMock()
    bio_c.canonical_code = "vitamin_d"
    bio_c.laboratory_flag = None
    bio_c.laboratory_provided_critical_flag = None
    bio_c.data_quality = "high"

    cat = MagicMock()
    cat.biomarkers = (bio_a, bio_b, bio_c)
    cat.attention_count = 2

    mock_dash = MagicMock()
    mock_dash.categories = (cat,)
    mock_dash.metadata.status.value = "ready"

    mock_bio_builder = MagicMock()
    mock_bio_builder.build.return_value = mock_dash

    provider = ProductionMorningBriefingInputProvider(
        morning_coach_use_case=mock_use_case,
        biomarkers_dashboard_builder=mock_bio_builder,
    )

    inp = provider.get_input()

    assert inp.biomarkers is not None
    assert inp.biomarkers.available_count == 3
    assert inp.biomarkers.attention_count == 2
    assert inp.biomarkers.critical_count == 1  # ONLY CRP had critical flag
    assert inp.biomarkers.data_status == "ready"

    # Signals must contain ferritin and crp, sorted strictly by canonical_code ("crp", "ferritin")
    signals = inp.biomarkers.signals
    assert len(signals) == 2

    assert signals[0].canonical_code == "crp"
    assert signals[0].interpretation == "CRITICAL"
    assert signals[0].data_quality == "medium"

    assert signals[1].canonical_code == "ferritin"
    assert signals[1].interpretation == "L"
    assert signals[1].data_quality == "high"
