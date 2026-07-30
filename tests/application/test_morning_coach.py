from datetime import datetime

from application import (
    AdaptationPolicy,
    AthleteAssessmentBuilder,
    AthleteKnowledgeContextBuilder,
    MorningCoachBuilder,
    MorningCoachReport,
    TrainingAssessment,
    TrainingAssessmentStatus,
)
from decision.engine import DecisionEngine
from planner.engine import PlannerEngine
from tests.helpers import build_athlete


def build_training(
    status: TrainingAssessmentStatus,
) -> TrainingAssessment:

    return TrainingAssessment(
        as_of=datetime(2026, 8, 7, 12, 0),
        period=None,
        status=status,
        supporting_patterns=(),
    )


def build_report(
    training_status: TrainingAssessmentStatus = TrainingAssessmentStatus.NO_CLEAR_PATTERN,
):

    athlete = build_athlete(recovery_score=70, fatigue=79)
    context = AthleteKnowledgeContextBuilder().build(
        as_of=datetime(2026, 8, 7, 12, 0),
        athlete_state=athlete,
    )
    assessment = AthleteAssessmentBuilder().build(
        context,
        build_training(training_status),
    )
    adaptation = AdaptationPolicy().evaluate(assessment)
    plan = DecisionEngine().decide(athlete, adaptation)
    workout = PlannerEngine().build(plan.decision, athlete)

    return athlete, assessment, adaptation, workout, MorningCoachBuilder().build(
        athlete,
        assessment,
        adaptation,
        workout,
    )


def test_report_preserves_existing_model_references():

    athlete, assessment, adaptation, workout, report = build_report()

    assert report.athlete_state is athlete
    assert report.athlete_assessment is assessment
    assert report.adaptation is adaptation
    assert report.workout is workout


def test_message_is_deterministic():

    athlete, assessment, adaptation, workout, first = build_report()
    second = MorningCoachBuilder().build(
        athlete,
        assessment,
        adaptation,
        workout,
    )

    assert first.message == second.message
    assert first.message == (
        "Dzisiaj zalecany trening: Endurance. "
        "Powód: Current plan is maintained."
    )


def test_builder_does_not_mutate_inputs():

    athlete, assessment, adaptation, workout, _ = build_report(
        TrainingAssessmentStatus.ATTENTION_REQUIRED,
    )
    original_recovery = athlete.recovery.score
    original_fatigue = athlete.performance.fatigue
    original_reasons = adaptation.source_reasons
    original_blocks = workout.blocks

    MorningCoachBuilder().build(athlete, assessment, adaptation, workout)

    assert athlete.recovery.score == original_recovery
    assert athlete.performance.fatigue == original_fatigue
    assert adaptation.source_reasons is original_reasons
    assert workout.blocks is original_blocks


def test_full_integration_builds_a_recovery_daily_brief():

    _, assessment, adaptation, workout, report = build_report(
        TrainingAssessmentStatus.ATTENTION_REQUIRED,
    )

    assert assessment.status.value == "caution"
    assert adaptation.status.value == "reduce_load"
    assert workout.name == "Recovery"
    assert report.message == (
        "Dzisiaj zalecany trening: Recovery. "
        "Powód: Long-term adaptation requires reduced load."
    )


def test_public_application_exports_are_available():

    assert MorningCoachBuilder.__name__ == "MorningCoachBuilder"
    assert MorningCoachReport.__name__ == "MorningCoachReport"
