from datetime import datetime

from application import AdaptationDirective, AdaptationStatus, AthleteAssessmentReason
from decision.engine import DecisionEngine
from decision.prescription.models import TrainingObjective

from tests.helpers import build_athlete

from workout.enums import WorkoutType


def build_adaptation(status: AdaptationStatus) -> AdaptationDirective:

    return AdaptationDirective(
        as_of=datetime(2026, 8, 7, 12, 0),
        status=status,
        source_reasons=(AthleteAssessmentReason.LOW_RECOVERY,),
    )


def test_recovery_rule_returns_recovery_workout():

    athlete = build_athlete(
        recovery_score=20,
        fatigue=70,
    )

    plan = DecisionEngine().decide(athlete)

    assert plan.recommendation == WorkoutType.RECOVERY


def test_decide_without_adaptation_preserves_existing_behavior():

    athlete = build_athlete(recovery_score=80, fatigue=30)

    plan = DecisionEngine().decide(athlete)

    assert plan.recommendation == WorkoutType.THRESHOLD


def test_decide_with_explicit_none_preserves_existing_behavior():

    athlete = build_athlete(recovery_score=80, fatigue=30)

    without_adaptation = DecisionEngine().decide(athlete)
    with_none = DecisionEngine().decide(athlete, adaptation=None)

    assert with_none == without_adaptation


def test_maintain_adaptation_preserves_existing_behavior():

    athlete = build_athlete(recovery_score=80, fatigue=30)

    plan = DecisionEngine().decide(
        athlete,
        build_adaptation(AdaptationStatus.MAINTAIN),
    )

    assert plan.recommendation == WorkoutType.THRESHOLD


def test_insufficient_data_adaptation_preserves_existing_behavior():

    athlete = build_athlete(recovery_score=80, fatigue=30)

    plan = DecisionEngine().decide(
        athlete,
        build_adaptation(AdaptationStatus.INSUFFICIENT_DATA),
    )

    assert plan.recommendation == WorkoutType.THRESHOLD


def test_reduce_load_adaptation_selects_existing_recovery_prescription():

    athlete = build_athlete(recovery_score=80, fatigue=30)

    plan = DecisionEngine().decide(
        athlete,
        build_adaptation(AdaptationStatus.REDUCE_LOAD),
    )

    assert plan.recommendation == WorkoutType.RECOVERY
    assert plan.decision.objective is TrainingObjective.RECOVERY
    assert plan.decision.duration == 45
    assert plan.decision.target_tss == 30


def test_reduce_load_adaptation_takes_precedence_over_peak_diagnosis():

    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=80)

    plan = DecisionEngine().decide(
        athlete,
        build_adaptation(AdaptationStatus.REDUCE_LOAD),
    )

    assert plan.recommendation == WorkoutType.RECOVERY


def test_decision_engine_does_not_mutate_athlete_or_adaptation():

    athlete = build_athlete(recovery_score=80, fatigue=30)
    adaptation = build_adaptation(AdaptationStatus.REDUCE_LOAD)
    original_recovery = athlete.recovery.score
    original_fatigue = athlete.performance.fatigue
    original_reasons = adaptation.source_reasons

    DecisionEngine().decide(athlete, adaptation)

    assert athlete.recovery.score == original_recovery
    assert athlete.performance.fatigue == original_fatigue
    assert adaptation.source_reasons is original_reasons
