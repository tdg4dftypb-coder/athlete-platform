from datetime import datetime

from application import AdaptationDirective, AdaptationStatus, AthleteAssessmentReason
from athlete.intelligence.models import AthleteInsight, AthleteInsightType
from decision.engine import DecisionEngine
from decision.prescription.models import DecisionReason, TrainingObjective

from tests.helpers import build_athlete

from workout.enums import WorkoutType


def build_adaptation(status: AdaptationStatus) -> AdaptationDirective:

    return AdaptationDirective(
        as_of=datetime(2026, 8, 7, 12, 0),
        status=status,
        source_reasons=(AthleteAssessmentReason.LOW_RECOVERY,),
    )


def build_insight(insight_type: AthleteInsightType) -> AthleteInsight:
    return AthleteInsight(
        id=f"{insight_type.value}:event-1",
        type=insight_type,
        confidence=1.0,
        evidence=("event-1",),
        as_of=datetime(2026, 8, 7, 12, 0),
    )


def test_decision_reason_has_one_canonical_public_import():
    import decision.models as decision_models

    assert DecisionReason.__module__ == (
        "decision.prescription.models.decision_reason"
    )
    assert not hasattr(decision_models, "DecisionReason")


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
    assert plan.decision.decision_reasons == ()


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


def test_need_more_recovery_insight_selects_recovery_instead_of_peak_training():
    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=80)
    insight = build_insight(AthleteInsightType.NEED_MORE_RECOVERY)

    plan = DecisionEngine().decide(athlete, insights=(insight,))

    assert plan.recommendation is WorkoutType.RECOVERY
    assert plan.decision.objective is TrainingObjective.RECOVERY
    assert plan.decision.decision_reasons == (
        DecisionReason.INSIGHT_NEED_MORE_RECOVERY,
    )


def test_fatigue_accumulating_insight_selects_recovery_instead_of_threshold():
    athlete = build_athlete(recovery_score=80, fatigue=30)
    insight = build_insight(AthleteInsightType.FATIGUE_ACCUMULATING)

    plan = DecisionEngine().decide(athlete, insights=(insight,))

    assert plan.recommendation is WorkoutType.RECOVERY
    assert plan.decision.decision_reasons == (
        DecisionReason.INSIGHT_FATIGUE_ACCUMULATING,
    )


def test_high_training_compliance_preserves_existing_progression_when_state_is_safe():
    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=80)
    insight = build_insight(AthleteInsightType.HIGH_TRAINING_COMPLIANCE)

    plan = DecisionEngine().decide(athlete, insights=(insight,))

    assert plan.recommendation is WorkoutType.VO2
    assert plan.decision.decision_reasons == (
        DecisionReason.INSIGHT_HIGH_TRAINING_COMPLIANCE,
    )


def test_insight_reason_order_is_stable_and_restrictive_insights_take_precedence():
    athlete = build_athlete(recovery_score=90, fatigue=20, freshness=80)
    insights = (
        build_insight(AthleteInsightType.HIGH_TRAINING_COMPLIANCE),
        build_insight(AthleteInsightType.FATIGUE_ACCUMULATING),
        build_insight(AthleteInsightType.NEED_MORE_RECOVERY),
    )

    plan = DecisionEngine().decide(athlete, insights=insights)

    assert plan.recommendation is WorkoutType.RECOVERY
    assert plan.decision.decision_reasons == (
        DecisionReason.INSIGHT_NEED_MORE_RECOVERY,
        DecisionReason.INSIGHT_FATIGUE_ACCUMULATING,
        DecisionReason.INSIGHT_HIGH_TRAINING_COMPLIANCE,
    )
    assert DecisionEngine().decide(athlete, insights=insights) == plan
