from datetime import datetime, timezone
from enum import Enum
from typing import Any

import pytest
from morning_briefing.domain import (
    MorningBriefing,
    MorningSection,
    MorningMetric,
    MorningRecommendation,
    MorningPriority,
    MorningStatus,
)
from morning_briefing.serialization import MorningBriefingSerializer


# ── Helpers ───────────────────────────────────────────────────────────────────

SERIALIZER = MorningBriefingSerializer()

_JSON_SAFE_TYPES = (dict, list, str, int, float, bool, type(None))


def _assert_json_safe(obj: Any, path: str = "root") -> None:
    """Recursively assert that all values are JSON-safe types."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, str), f"Dict key at {path} is not a str: {k!r}"
            _assert_json_safe(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_json_safe(v, f"{path}[{i}]")
    else:
        assert isinstance(obj, _JSON_SAFE_TYPES), (
            f"Non-JSON-safe value at {path}: {obj!r} (type={type(obj).__name__})"
        )


def _make_briefing(
    *,
    sections=(),
    status=MorningStatus.READY,
    generated_at=datetime(2026, 8, 6, 12, 0, 0),
):
    return MorningBriefing(generated_at=generated_at, status=status, sections=tuple(sections))


def _make_full_section():
    metric = MorningMetric(title="Recovery score", value=85, unit="%", status="good")
    rec = MorningRecommendation(
        title="Proceed as planned",
        description="Recovery indicators support the planned training session.",
        priority=MorningPriority.LOW,
    )
    return MorningSection(
        title="Recovery",
        summary="All good.",
        metrics=(metric,),
        recommendations=(rec,),
    )


# ── Contract shape ────────────────────────────────────────────────────────────

def test_top_level_keys():
    briefing = _make_briefing()
    result = SERIALIZER.serialize(briefing)
    assert set(result.keys()) == {"generated_at", "status", "sections"}


def test_section_keys():
    briefing = _make_briefing(sections=[_make_full_section()])
    result = SERIALIZER.serialize(briefing)
    section = result["sections"][0]
    assert set(section.keys()) == {"title", "summary", "metrics", "recommendations"}


def test_metric_keys():
    briefing = _make_briefing(sections=[_make_full_section()])
    result = SERIALIZER.serialize(briefing)
    metric = result["sections"][0]["metrics"][0]
    assert set(metric.keys()) == {"title", "value", "unit", "status"}


def test_recommendation_keys():
    briefing = _make_briefing(sections=[_make_full_section()])
    result = SERIALIZER.serialize(briefing)
    rec = result["sections"][0]["recommendations"][0]
    assert set(rec.keys()) == {"title", "description", "priority"}


# ── datetime ─────────────────────────────────────────────────────────────────

def test_generated_at_iso_8601():
    dt = datetime(2026, 8, 6, 12, 30, 45)
    briefing = _make_briefing(generated_at=dt)
    result = SERIALIZER.serialize(briefing)
    assert result["generated_at"] == "2026-08-06T12:30:45"


def test_generated_at_with_timezone_preserved():
    dt = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)
    briefing = _make_briefing(generated_at=dt)
    result = SERIALIZER.serialize(briefing)
    assert result["generated_at"] == "2026-08-06T12:00:00+00:00"


# ── Enum serialization ────────────────────────────────────────────────────────

@pytest.mark.parametrize("status, expected", [
    (MorningStatus.READY, "ready"),
    (MorningStatus.PARTIAL, "partial"),
    (MorningStatus.UNAVAILABLE, "unavailable"),
    (MorningStatus.STALE, "stale"),
])
def test_all_morning_status_lowercase(status, expected):
    briefing = _make_briefing(status=status)
    result = SERIALIZER.serialize(briefing)
    assert result["status"] == expected


@pytest.mark.parametrize("priority, expected", [
    (MorningPriority.LOW, "low"),
    (MorningPriority.MEDIUM, "medium"),
    (MorningPriority.HIGH, "high"),
    (MorningPriority.CRITICAL, "critical"),
])
def test_all_morning_priority_lowercase(priority, expected):
    rec = MorningRecommendation(title="T", description="D", priority=priority)
    section = MorningSection(title="Recovery", summary="S", metrics=(), recommendations=(rec,))
    briefing = _make_briefing(sections=[section])
    result = SERIALIZER.serialize(briefing)
    assert result["sections"][0]["recommendations"][0]["priority"] == expected


# ── None handling ─────────────────────────────────────────────────────────────

def test_none_unit_remains_none():
    metric = MorningMetric(title="Recovery status", value="Good", unit=None, status="info")
    section = MorningSection(title="Recovery", summary="S", metrics=(metric,), recommendations=())
    briefing = _make_briefing(sections=[section])
    result = SERIALIZER.serialize(briefing)
    assert result["sections"][0]["metrics"][0]["unit"] is None


def test_none_value_remains_none():
    metric = MorningMetric(title="Recovery score", value=None, unit="%", status="info")
    section = MorningSection(title="Recovery", summary="S", metrics=(metric,), recommendations=())
    briefing = _make_briefing(sections=[section])
    result = SERIALIZER.serialize(briefing)
    assert result["sections"][0]["metrics"][0]["value"] is None


# ── Empty collections ─────────────────────────────────────────────────────────

def test_empty_sections():
    briefing = _make_briefing(sections=[])
    result = SERIALIZER.serialize(briefing)
    assert result["sections"] == []


def test_empty_metrics():
    section = MorningSection(title="Recovery", summary="S", metrics=(), recommendations=())
    briefing = _make_briefing(sections=[section])
    result = SERIALIZER.serialize(briefing)
    assert result["sections"][0]["metrics"] == []


def test_empty_recommendations():
    section = MorningSection(title="Recovery", summary="S", metrics=(), recommendations=())
    briefing = _make_briefing(sections=[section])
    result = SERIALIZER.serialize(briefing)
    assert result["sections"][0]["recommendations"] == []


# ── Order preservation ────────────────────────────────────────────────────────

def test_sections_order_preserved():
    s1 = MorningSection(title="Recovery", summary="A", metrics=(), recommendations=())
    s2 = MorningSection(title="Training", summary="B", metrics=(), recommendations=())
    s3 = MorningSection(title="Biomarkers", summary="C", metrics=(), recommendations=())
    briefing = _make_briefing(sections=[s1, s2, s3])
    result = SERIALIZER.serialize(briefing)
    titles = [s["title"] for s in result["sections"]]
    assert titles == ["Recovery", "Training", "Biomarkers"]


def test_recommendations_order_preserved():
    rec1 = MorningRecommendation(title="First", description="A", priority=MorningPriority.HIGH)
    rec2 = MorningRecommendation(title="Second", description="B", priority=MorningPriority.LOW)
    section = MorningSection(title="Recovery", summary="S", metrics=(), recommendations=(rec1, rec2))
    briefing = _make_briefing(sections=[section])
    result = SERIALIZER.serialize(briefing)
    recs = result["sections"][0]["recommendations"]
    assert recs[0]["title"] == "First"
    assert recs[1]["title"] == "Second"


# ── JSON safety ───────────────────────────────────────────────────────────────

def test_no_enum_objects_in_result():
    briefing = _make_briefing(sections=[_make_full_section()], status=MorningStatus.STALE)
    result = SERIALIZER.serialize(briefing)
    _assert_json_safe(result)


def test_full_briefing_json_safe():
    sections = [
        _make_full_section(),
        MorningSection(
            title="Biomarkers",
            summary="Two markers need attention.",
            metrics=(
                MorningMetric(title="Available results", value=5, unit=None, status="info"),
                MorningMetric(title="Results requiring attention", value=2, unit=None, status="warning"),
            ),
            recommendations=(
                MorningRecommendation(
                    title="Review laboratory results",
                    description="One or more laboratory results require attention.",
                    priority=MorningPriority.HIGH,
                ),
            ),
        ),
    ]
    briefing = _make_briefing(sections=sections, status=MorningStatus.PARTIAL)
    result = SERIALIZER.serialize(briefing)
    _assert_json_safe(result)


# ── Immutability ──────────────────────────────────────────────────────────────

def test_original_briefing_unchanged():
    briefing = _make_briefing(sections=[_make_full_section()])
    original_status = briefing.status
    original_sections_len = len(briefing.sections)
    SERIALIZER.serialize(briefing)
    assert briefing.status == original_status
    assert len(briefing.sections) == original_sections_len
