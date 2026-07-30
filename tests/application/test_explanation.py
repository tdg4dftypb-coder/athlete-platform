from datetime import datetime

from application import (
    AdaptationDirective,
    AdaptationStatus,
    AthleteAssessment,
    AthleteAssessmentReason,
    AthleteAssessmentStatus,
    ExplanationBuilder,
    ExplanationReport,
    TrainingAssessment,
    TrainingAssessmentStatus,
)
from planner.models import PlannedWorkout


def build_assessment() -> AthleteAssessment:

    return AthleteAssessment(
        as_of=datetime(2026, 8, 7, 12, 0),
        status=AthleteAssessmentStatus.CAUTION,
        training_assessment=TrainingAssessment(
            as_of=datetime(2026, 8, 7, 12, 0),
            period=None,
            status=TrainingAssessmentStatus.ATTENTION_REQUIRED,
            supporting_patterns=(),
        ),
        reasons=(AthleteAssessmentReason.LOW_RECOVERY,),
    )


def build_adaptation() -> AdaptationDirective:

    return AdaptationDirective(
        as_of=datetime(2026, 8, 7, 12, 0),
        status=AdaptationStatus.REDUCE_LOAD,
        source_reasons=(AthleteAssessmentReason.LOW_RECOVERY,),
    )


def build_workout() -> PlannedWorkout:

    return PlannedWorkout(
        name="Recovery",
        sport="cycling",
        target_tss=25.0,
        estimated_duration=60,
        blocks=[],
    )


def test_explanation_builder_is_deterministic_and_preserves_inputs():

    assessment = build_assessment()
    adaptation = build_adaptation()
    workout = build_workout()
    original_reasons = assessment.reasons
    original_source_reasons = adaptation.source_reasons
    original_blocks = workout.blocks

    first = ExplanationBuilder().build(assessment, adaptation, workout)
    second = ExplanationBuilder().build(assessment, adaptation, workout)

    assert first == second
    assert first.summary == "Today's recommendation: Recovery ride."
    assert first.reasons == (
        "Recovery status requires reduced load.",
        "Long-term adaptation recommends recovery.",
        "Recovery workout has been selected.",
    )
    assert assessment.reasons is original_reasons
    assert adaptation.source_reasons is original_source_reasons
    assert workout.blocks is original_blocks


def test_explanation_report_is_immutable():

    report = ExplanationReport(
        summary="Today's recommendation: Recovery ride.",
        reasons=(),
    )

    try:
        report.summary = "Changed"
    except AttributeError:
        pass
    else:
        raise AssertionError("ExplanationReport must be immutable")


def test_public_application_exports_are_available():

    assert ExplanationBuilder.__name__ == "ExplanationBuilder"
    assert ExplanationReport.__name__ == "ExplanationReport"
