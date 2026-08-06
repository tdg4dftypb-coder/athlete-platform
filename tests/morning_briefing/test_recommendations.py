from datetime import datetime
import pytest
from morning_briefing.domain import (
    MorningBriefing,
    MorningSection,
    MorningMetric,
    MorningRecommendation,
    MorningPriority,
    MorningStatus,
)
from morning_briefing.recommendations import MorningRecommendationEngine


def _make_recovery_section(score_value, *, extra_recs=()):
    return MorningSection(
        title="Recovery",
        summary="Recovery summary.",
        metrics=(
            MorningMetric(title="Recovery score", value=score_value, unit="%", status="info"),
            MorningMetric(title="Recovery status", value="Good", unit=None, status="info"),
        ),
        recommendations=extra_recs,
    )


def _make_biomarker_section(attention_count, *, extra_recs=()):
    return MorningSection(
        title="Biomarkers",
        summary="Biomarker summary.",
        metrics=(
            MorningMetric(title="Available results", value=5, unit=None, status="info"),
            MorningMetric(title="Results requiring attention", value=attention_count, unit=None, status="info"),
        ),
        recommendations=extra_recs,
    )


def _make_briefing(sections, status=MorningStatus.READY):
    return MorningBriefing(
        generated_at=datetime(2026, 8, 6, 12, 0, 0),
        status=status,
        sections=tuple(sections),
    )


engine = MorningRecommendationEngine()


# ── Recovery score rules ────────────────────────────────────────────────────

def test_recovery_score_below_50_high_priority():
    briefing = _make_briefing([_make_recovery_section(49)])
    result = engine.apply(briefing)
    recs = result.sections[0].recommendations
    assert len(recs) == 1
    assert recs[0].title == "Prioritize recovery"
    assert recs[0].priority == MorningPriority.HIGH


def test_recovery_score_50_medium_priority():
    briefing = _make_briefing([_make_recovery_section(50)])
    result = engine.apply(briefing)
    recs = result.sections[0].recommendations
    assert len(recs) == 1
    assert recs[0].title == "Train conservatively"
    assert recs[0].priority == MorningPriority.MEDIUM


def test_recovery_score_69_medium_priority():
    briefing = _make_briefing([_make_recovery_section(69)])
    result = engine.apply(briefing)
    recs = result.sections[0].recommendations
    assert len(recs) == 1
    assert recs[0].title == "Train conservatively"
    assert recs[0].priority == MorningPriority.MEDIUM


def test_recovery_score_70_low_priority():
    briefing = _make_briefing([_make_recovery_section(70)])
    result = engine.apply(briefing)
    recs = result.sections[0].recommendations
    assert len(recs) == 1
    assert recs[0].title == "Proceed as planned"
    assert recs[0].priority == MorningPriority.LOW


def test_no_recovery_section_no_recovery_rec():
    briefing = _make_briefing([_make_biomarker_section(0)])
    result = engine.apply(briefing)
    assert result.sections[0].title == "Biomarkers"
    assert result.sections[0].recommendations == ()


def test_invalid_recovery_score_no_exception():
    section = MorningSection(
        title="Recovery",
        summary="Recovery summary.",
        metrics=(
            MorningMetric(title="Recovery score", value="not_a_number", unit="%", status="info"),
        ),
        recommendations=(),
    )
    briefing = _make_briefing([section])
    result = engine.apply(briefing)
    # No crash, no recommendation added
    assert result.sections[0].recommendations == ()


def test_none_recovery_score_no_exception():
    section = MorningSection(
        title="Recovery",
        summary="Recovery summary.",
        metrics=(
            MorningMetric(title="Recovery score", value=None, unit="%", status="info"),
        ),
        recommendations=(),
    )
    briefing = _make_briefing([section])
    result = engine.apply(briefing)
    assert result.sections[0].recommendations == ()


# ── Biomarker rules ──────────────────────────────────────────────────────────

def test_biomarker_attention_above_zero_high_priority():
    briefing = _make_briefing([_make_biomarker_section(2)])
    result = engine.apply(briefing)
    recs = result.sections[0].recommendations
    assert len(recs) == 1
    assert recs[0].title == "Review laboratory results"
    assert recs[0].priority == MorningPriority.HIGH


def test_biomarker_attention_zero_no_rec():
    briefing = _make_briefing([_make_biomarker_section(0)])
    result = engine.apply(briefing)
    assert result.sections[0].recommendations == ()


# ── STALE rules ──────────────────────────────────────────────────────────────

def test_stale_briefing_adds_refresh_rec_to_first_section():
    briefing = _make_briefing(
        [_make_recovery_section(80), _make_biomarker_section(0)],
        status=MorningStatus.STALE,
    )
    result = engine.apply(briefing)
    first_recs = result.sections[0].recommendations
    titles = [r.title for r in first_recs]
    assert "Refresh source data" in titles


def test_stale_with_no_sections_no_new_section():
    briefing = _make_briefing([], status=MorningStatus.STALE)
    result = engine.apply(briefing)
    assert len(result.sections) == 0


# ── Immutability & idempotency ────────────────────────────────────────────────

def test_original_briefing_unchanged():
    briefing = _make_briefing([_make_recovery_section(40)])
    result = engine.apply(briefing)
    assert briefing.sections[0].recommendations == ()
    assert len(result.sections[0].recommendations) == 1


def test_result_uses_immutable_tuples():
    briefing = _make_briefing([_make_recovery_section(80), _make_biomarker_section(1)])
    result = engine.apply(briefing)
    assert isinstance(result.sections, tuple)
    assert isinstance(result.sections[0].recommendations, tuple)


def test_double_apply_no_duplicate_recommendations():
    briefing = _make_briefing([_make_recovery_section(40), _make_biomarker_section(2)])
    once = engine.apply(briefing)
    twice = engine.apply(once)
    # Each section should still have exactly the same number of recs
    assert len(twice.sections[0].recommendations) == len(once.sections[0].recommendations)
    assert len(twice.sections[1].recommendations) == len(once.sections[1].recommendations)


def test_existing_recommendations_preserved():
    existing_rec = MorningRecommendation(
        title="Custom rec",
        description="Already added.",
        priority=MorningPriority.LOW,
    )
    briefing = _make_briefing([_make_recovery_section(80, extra_recs=(existing_rec,))])
    result = engine.apply(briefing)
    titles = [r.title for r in result.sections[0].recommendations]
    assert "Custom rec" in titles
    assert "Proceed as planned" in titles
