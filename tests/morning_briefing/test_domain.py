from datetime import datetime
from dataclasses import FrozenInstanceError
import pytest
from morning_briefing.domain import (
    MorningStatus,
    MorningPriority,
    MorningMetric,
    MorningRecommendation,
    MorningSection,
    MorningBriefing,
)


def test_enums() -> None:
    assert MorningStatus.READY == "ready"
    assert MorningStatus.PARTIAL == "partial"
    assert MorningStatus.UNAVAILABLE == "unavailable"
    assert MorningStatus.STALE == "stale"

    assert MorningPriority.LOW == "low"
    assert MorningPriority.MEDIUM == "medium"
    assert MorningPriority.HIGH == "high"
    assert MorningPriority.CRITICAL == "critical"


def test_metric_creation_and_immutability() -> None:
    metric = MorningMetric(title="Tętno spoczynkowe", value=54, unit="bpm", status="normal")
    assert metric.title == "Tętno spoczynkowe"
    assert metric.value == 54
    assert metric.unit == "bpm"
    assert metric.status == "normal"

    with pytest.raises(FrozenInstanceError):
        # Should raise FrozenInstanceError because of frozen=True
        metric.title = "Nowy tytuł"  # type: ignore


def test_recommendation_creation_and_immutability() -> None:
    rec = MorningRecommendation(
        title="Dłuższa rozgrzewka",
        description="Twoja zmienność tętna jest niska.",
        priority=MorningPriority.HIGH,
    )
    assert rec.title == "Dłuższa rozgrzewka"
    assert rec.priority == MorningPriority.HIGH

    with pytest.raises(FrozenInstanceError):
        rec.priority = MorningPriority.CRITICAL  # type: ignore


def test_section_and_briefing_aggregation() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    metric = MorningMetric(title="Sen", value=7.5, unit="h", status="good")
    rec = MorningRecommendation(title="Unikaj kofeiny", description="Przed snem.", priority=MorningPriority.MEDIUM)

    section = MorningSection(
        title="Regeneracja",
        summary="Twój sen był poprawny.",
        metrics=(metric,),
        recommendations=(rec,),
    )

    briefing = MorningBriefing(
        generated_at=now,
        status=MorningStatus.READY,
        sections=(section,),
    )

    assert briefing.generated_at == now
    assert briefing.status == MorningStatus.READY
    assert len(briefing.sections) == 1
    assert briefing.sections[0].title == "Regeneracja"
    assert briefing.sections[0].metrics[0].title == "Sen"
    assert briefing.sections[0].recommendations[0].title == "Unikaj kofeiny"


def test_equality() -> None:
    metric1 = MorningMetric(title="Sen", value=8, unit="h", status="good")
    metric2 = MorningMetric(title="Sen", value=8, unit="h", status="good")
    metric3 = MorningMetric(title="Sen", value=7, unit="h", status="warning")

    assert metric1 == metric2
    assert metric1 != metric3


def test_repr() -> None:
    metric = MorningMetric(title="Sen", value=8, unit="h", status="good")
    representation = repr(metric)
    assert "MorningMetric" in representation
    assert "title='Sen'" in representation
    assert "value=8" in representation
