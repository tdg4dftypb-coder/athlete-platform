from datetime import datetime
from morning_briefing.domain import MorningStatus
from morning_briefing.input_models import (
    MorningBriefingInput,
    RecoveryBriefingInput,
    TrainingBriefingInput,
    BiomarkerBriefingInput,
)
from morning_briefing.builder import MorningBriefingBuilder


def test_builder_all_three_sections_ready() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    rec_input = RecoveryBriefingInput(score=85, status="Good", summary="Wszystko super.", is_stale=False)
    trn_input = TrainingBriefingInput(
        title="Długi bieg",
        description="Bieg tlenowy.",
        duration_minutes=90,
        intensity="moderate",
        is_available=True,
    )
    bio_input = BiomarkerBriefingInput(available_count=5, attention_count=0, summary="Brak uwag.", is_stale=False)

    input_data = MorningBriefingInput(generated_at=now, recovery=rec_input, training=trn_input, biomarkers=bio_input)

    builder = MorningBriefingBuilder()
    briefing = builder.build(input_data)

    assert briefing.status == MorningStatus.READY
    assert len(briefing.sections) == 3

    # Recovery section check
    assert briefing.sections[0].title == "Recovery"
    assert briefing.sections[0].summary == "Wszystko super."
    assert briefing.sections[0].metrics[0].value == 85
    assert briefing.sections[0].metrics[1].value == "Good"
    assert briefing.sections[0].recommendations == ()

    # Training section check
    assert briefing.sections[1].title == "Training"
    assert briefing.sections[1].summary == "Bieg tlenowy."
    assert briefing.sections[1].metrics[0].value == "Długi bieg"
    assert briefing.sections[1].metrics[1].value == 90
    assert briefing.sections[1].metrics[2].value == "moderate"

    # Biomarkers section check
    assert briefing.sections[2].title == "Biomarkers"
    assert briefing.sections[2].summary == "Brak uwag."
    assert briefing.sections[2].metrics[0].value == 5
    assert briefing.sections[2].metrics[1].value == 0


def test_builder_training_not_available_partial() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    rec_input = RecoveryBriefingInput(score=85, status="Good", summary="Wszystko super.", is_stale=False)
    trn_input = TrainingBriefingInput(
        title=None,
        description=None,
        duration_minutes=None,
        intensity=None,
        is_available=False,
    )
    bio_input = BiomarkerBriefingInput(available_count=5, attention_count=0, summary="Brak uwag.", is_stale=False)

    input_data = MorningBriefingInput(generated_at=now, recovery=rec_input, training=trn_input, biomarkers=bio_input)

    builder = MorningBriefingBuilder()
    briefing = builder.build(input_data)

    assert briefing.status == MorningStatus.PARTIAL
    # Training section is not created
    assert len(briefing.sections) == 2
    assert briefing.sections[0].title == "Recovery"
    assert briefing.sections[1].title == "Biomarkers"


def test_builder_only_recovery_partial() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    rec_input = RecoveryBriefingInput(score=85, status="Good", summary="Wszystko super.", is_stale=False)

    input_data = MorningBriefingInput(generated_at=now, recovery=rec_input, training=None, biomarkers=None)

    builder = MorningBriefingBuilder()
    briefing = builder.build(input_data)

    assert briefing.status == MorningStatus.PARTIAL
    assert len(briefing.sections) == 1
    assert briefing.sections[0].title == "Recovery"


def test_builder_all_absent_unavailable() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    input_data = MorningBriefingInput(generated_at=now, recovery=None, training=None, biomarkers=None)

    builder = MorningBriefingBuilder()
    briefing = builder.build(input_data)

    assert briefing.status == MorningStatus.UNAVAILABLE
    assert len(briefing.sections) == 0


def test_builder_stale_recovery_stale() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    rec_input = RecoveryBriefingInput(score=85, status="Good", summary="Wszystko super.", is_stale=True)
    trn_input = TrainingBriefingInput(
        title="Długi bieg",
        description="Bieg tlenowy.",
        duration_minutes=90,
        intensity="moderate",
        is_available=True,
    )
    bio_input = BiomarkerBriefingInput(available_count=5, attention_count=0, summary="Brak uwag.", is_stale=False)

    input_data = MorningBriefingInput(generated_at=now, recovery=rec_input, training=trn_input, biomarkers=bio_input)

    builder = MorningBriefingBuilder()
    briefing = builder.build(input_data)

    assert briefing.status == MorningStatus.STALE


def test_builder_stale_biomarkers_stale() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    rec_input = RecoveryBriefingInput(score=85, status="Good", summary="Wszystko super.", is_stale=False)
    bio_input = BiomarkerBriefingInput(available_count=5, attention_count=0, summary="Brak uwag.", is_stale=True)

    input_data = MorningBriefingInput(generated_at=now, recovery=rec_input, training=None, biomarkers=bio_input)

    builder = MorningBriefingBuilder()
    briefing = builder.build(input_data)

    assert briefing.status == MorningStatus.STALE


def test_biomarker_attention_badge_warning_status() -> None:
    now = datetime(2026, 8, 6, 12, 0, 0)
    bio_input = BiomarkerBriefingInput(available_count=5, attention_count=2, summary="Uwaga.", is_stale=False)
    input_data = MorningBriefingInput(generated_at=now, recovery=None, training=None, biomarkers=bio_input)

    builder = MorningBriefingBuilder()
    briefing = builder.build(input_data)

    assert briefing.sections[0].metrics[1].title == "Results requiring attention"
    assert briefing.sections[0].metrics[1].value == 2
    assert briefing.sections[0].metrics[1].status == "warning"
