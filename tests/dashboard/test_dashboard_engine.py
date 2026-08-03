from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from adaptive import (
    AthleteGoal,
    AthleteGoalType,
    BodyMassTrendQuality,
    BodyMassTrendQualityDataStatus,
    GoalAssessment,
    GoalAssessmentDataStatus,
)
from application.decision_explainability import ExplainabilityResult
from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionProfile,
    BodyMassTrend,
    BodyMeasurement,
)
from core.models import HealthDaily
from dashboard import (
    DASHBOARD_CONTRACT_VERSION,
    DashboardEngine,
    DashboardSectionStatus,
)
from decision.models import DecisionResult
from decision.prescription.models import DecisionReason, TrainingObjective
from decision.sports import Sport
from nutrition import (
    EnergyRequirement,
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionAssessment,
    NutritionDataStatus,
)
from performance.models import PerformanceState
from performance.training_load import TrainingLoad
from planner.models import PlannedWorkout
from recommendation import (
    Recommendation,
    RecommendationPriority,
    RecommendationResult,
    RecommendationType,
)
from recovery.models import RecoveryMetric, RecoveryResult
from workout.enums import WorkoutType


VALID_FOR_DATE = date(2026, 8, 3)
AS_OF = datetime(2026, 8, 3, 6)


def _health() -> HealthDaily:
    return HealthDaily(
        date=VALID_FOR_DATE,
        hrv=42,
        resting_hr=51,
        sleep_duration=465,
        steps=8200,
        active_energy=620,
        resting_energy=1780,
        respiratory_rate=14.2,
        spo2=98.0,
        wrist_temperature=36.1,
    )


def _recovery() -> RecoveryResult:
    metric = RecoveryMetric(
        value=80.0,
        baseline=75.0,
        delta=5.0,
        delta_percent=6.7,
        score=88,
    )
    return RecoveryResult(
        score=84,
        status="legacy presentation value",
        reasons=["legacy presentation reason"],
        hrv=metric,
        resting_hr=metric,
        sleep=RecoveryMetric(
            value=7.75,
            baseline=7.5,
            delta=0.25,
            delta_percent=3.3,
            score=91,
        ),
    )


def _performance() -> PerformanceState:
    weekly = TrainingLoad(310.0, 62.0, 5, 44.3, 7)
    monthly = TrainingLoad(1210.0, 57.6, 21, 28.8, 42)
    return PerformanceState(
        weekly=weekly,
        monthly=monthly,
        atl=44.3,
        ctl=28.8,
        tsb=-15.5,
        fatigue=44.3,
        fitness=28.8,
        freshness=-15.5,
    )


def _decision(
    *,
    objective: TrainingObjective = TrainingObjective.ENDURANCE,
) -> DecisionResult:
    return DecisionResult(
        sport=Sport.CYCLING,
        recommendation=WorkoutType.ENDURANCE,
        duration=75,
        target_tss=62.0,
        intensity="endurance",
        reasons=["legacy reason"],
        objective=objective,
        decision_reasons=(DecisionReason.INSIGHT_NEED_MORE_RECOVERY,),
    )


def _planned_workout() -> PlannedWorkout:
    return PlannedWorkout(
        name="Endurance 75",
        sport="cycling",
        target_tss=62.0,
        estimated_duration=75,
        blocks=[],
    )


def _nutrition(
    status: NutritionDataStatus = NutritionDataStatus.COMPLETE,
    *,
    as_of: datetime = AS_OF,
    evidence: tuple[str, ...] = ("nutrition:b", "nutrition:a"),
    limitations: tuple[str, ...] = ("missing_energy_intake",),
) -> NutritionAssessment:
    return NutritionAssessment(
        energy_requirement=EnergyRequirement(
            estimated_daily_requirement_kcal=None,
            observed_daily_expenditure_kcal=2400.0,
            resting_energy_kcal=1780.0,
            active_energy_kcal=620.0,
        ),
        macro_targets=MacroTargets(
            carbohydrate_g=360.0,
            protein_g=128.0,
            carbohydrate_g_per_kg=4.5,
            protein_g_per_kg=1.6,
        ),
        fueling_plan=FuelingPlan(
            pre_workout_carbohydrate_g=40.0,
            during_workout_carbohydrate_g_per_hour=30.0,
            post_workout_carbohydrate_g=80.0,
            post_workout_protein_g=24.0,
        ),
        hydration_target=HydrationTarget(
            daily_ml=2800.0,
            during_workout_ml_per_hour=600.0,
        ),
        data_status=status,
        confidence=0.75,
        evidence=evidence,
        limitations=limitations,
        valid_for_date=VALID_FOR_DATE,
        as_of=as_of,
    )


def _body_composition(
    status: BodyCompositionDataStatus = BodyCompositionDataStatus.COMPLETE,
    *,
    as_of: datetime = AS_OF,
    limitations: tuple[str, ...] = ("missing_visceral_fat",),
) -> BodyCompositionAssessment:
    current = BodyMeasurement(80.0, as_of - timedelta(days=1))
    baseline = BodyMeasurement(81.5, as_of - timedelta(days=29))
    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(
            body_mass=current,
            body_fat=BodyMeasurement(17.0, as_of - timedelta(days=1)),
            muscle_mass=BodyMeasurement(61.0, as_of - timedelta(days=1)),
            body_water=BodyMeasurement(55.0, as_of - timedelta(days=1)),
            basal_metabolic_rate=BodyMeasurement(
                1750.0,
                as_of - timedelta(days=1),
            ),
            waist_circumference=BodyMeasurement(
                82.0,
                as_of - timedelta(days=1),
            ),
        ),
        body_mass_trend=BodyMassTrend(
            current=current,
            baseline=baseline,
            period_days=28,
            absolute_change_kg=-1.5,
            percentage_change=-1.84,
        ),
        data_status=status,
        confidence=0.875,
        evidence=("body:b", "body:a"),
        limitations=limitations,
        valid_for_date=VALID_FOR_DATE,
        as_of=as_of,
    )


def _goal(
    status: GoalAssessmentDataStatus = GoalAssessmentDataStatus.COMPLETE,
    *,
    as_of: datetime = AS_OF,
    limitations: tuple[str, ...] = (),
) -> GoalAssessment:
    goal = AthleteGoal(
        id="goal-1",
        goal_type=AthleteGoalType.REDUCE_BODY_MASS,
        target_body_mass_kg=77.0,
        valid_from=date(2026, 7, 1),
        valid_until=date(2026, 10, 1),
        recorded_at=as_of - timedelta(days=40),
        evidence=("goal:configured",),
    )
    return GoalAssessment(
        goal=goal,
        data_status=status,
        confidence=0.8,
        evidence=("goal:b", "goal:a"),
        limitations=limitations,
        valid_for_date=VALID_FOR_DATE,
        as_of=as_of,
    )


def _trend_quality(
    *,
    as_of: datetime = AS_OF,
    limitations: tuple[str, ...] = ("source_consistency_unknown",),
) -> BodyMassTrendQuality:
    return BodyMassTrendQuality(
        measurement_count=4,
        period_days=28,
        current_is_fresh=True,
        baseline_window_valid=True,
        source_consistency_known=False,
        data_status=BodyMassTrendQualityDataStatus.PARTIAL,
        confidence=0.75,
        evidence=("trend:b", "trend:a"),
        limitations=limitations,
        valid_for_date=VALID_FOR_DATE,
        as_of=as_of,
    )


def _recommendation(
    recommendation_id: str,
    recommendation_type: RecommendationType,
    *,
    evidence: tuple[str, ...],
) -> Recommendation:
    return Recommendation(
        id=recommendation_id,
        type=recommendation_type,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.8,
        evidence=evidence,
        source_rules=("RuleB", "RuleA", "RuleB"),
        as_of=AS_OF,
    )


def _recommendation_result() -> RecommendationResult:
    return RecommendationResult(
        recommendations=(
            _recommendation(
                "hydration",
                RecommendationType.INCREASE_HYDRATION,
                evidence=("water:b", "water:a", "water:b"),
            ),
            _recommendation(
                "sleep",
                RecommendationType.EXTEND_SLEEP,
                evidence=("sleep:a",),
            ),
        ),
        as_of=AS_OF,
    )


def _explainability(
    messages: tuple[str, ...] = (
        "Increase hydration.",
        "Extend sleep duration.",
    ),
) -> ExplainabilityResult:
    return ExplainabilityResult(
        summary="Decision factors identified.",
        contributing_factors=(),
        recommendations=messages,
    )


def _build(**changes):
    arguments = {
        "valid_for_date": VALID_FOR_DATE,
        "as_of": AS_OF,
        "health": None,
        "recovery": None,
        "performance": None,
        "decision": None,
        "planned_workout": None,
        "nutrition": None,
        "body_composition": None,
        "body_mass_trend_quality": None,
        "goal": None,
        "recommendation_result": None,
        "explainability": None,
    }
    arguments.update(changes)
    return DashboardEngine().build(**arguments)


def _full_inputs():
    return {
        "health": _health(),
        "recovery": _recovery(),
        "performance": _performance(),
        "decision": _decision(),
        "planned_workout": _planned_workout(),
        "nutrition": _nutrition(),
        "body_composition": _body_composition(),
        "body_mass_trend_quality": _trend_quality(),
        "goal": _goal(),
        "recommendation_result": _recommendation_result(),
        "explainability": _explainability(),
    }


def test_full_dashboard_maps_only_ready_canonical_values():
    dashboard = _build(**_full_inputs())

    assert dashboard.contract_version == DASHBOARD_CONTRACT_VERSION
    assert dashboard.valid_for_date == VALID_FOR_DATE
    assert dashboard.as_of == AS_OF
    assert dashboard.health.hrv_ms == 42
    assert dashboard.health.resting_heart_rate_bpm == 51
    assert dashboard.health.sleep_minutes == 465
    assert dashboard.health.steps == 8200
    assert dashboard.health.active_energy_kcal == 620
    assert dashboard.health.resting_energy_kcal == 1780
    assert dashboard.health.respiratory_rate_per_minute == 14.2
    assert dashboard.health.oxygen_saturation_percent == 98.0
    assert dashboard.health.wrist_temperature_celsius == 36.1
    assert dashboard.recovery.recovery_score == 84
    assert dashboard.recovery.sleep_score == 91
    assert dashboard.performance.weekly_training_load_tss == 310.0
    assert dashboard.performance.monthly_training_load_tss == 1210.0
    assert dashboard.performance.fatigue_tss_per_day == 44.3
    assert dashboard.performance.fitness_tss_per_day == 28.8
    assert dashboard.performance.form_tss_per_day == -15.5
    assert dashboard.training.workout_name == "Endurance 75"
    assert dashboard.training.workout_goal == "ENDURANCE"
    assert dashboard.training.estimated_duration_minutes == 75
    assert dashboard.training.target_tss == 62.0
    assert dashboard.training.target_if is None
    assert dashboard.training.decision_action == "endurance"
    assert dashboard.training.decision_reasons == (
        "insight_need_more_recovery",
    )


def test_nutrition_targets_are_mapped_without_energy_balance():
    section = _build(nutrition=_nutrition()).nutrition

    assert section.metadata.status is DashboardSectionStatus.READY
    assert section.metadata.completeness_score == 0.75
    assert section.observed_daily_expenditure_kcal == 2400.0
    assert section.estimated_daily_requirement_kcal is None
    assert section.carbohydrate_target_g == 360.0
    assert section.protein_target_g == 128.0
    assert section.carbohydrate_target_g_per_kg == 4.5
    assert section.protein_target_g_per_kg == 1.6
    assert section.hydration_daily_ml == 2800.0
    assert section.hydration_during_workout_ml_per_hour == 600.0
    assert section.fueling_pre_workout_carbohydrate_g == 40.0
    assert section.fueling_during_workout_carbohydrate_g_per_hour == 30.0
    assert section.fueling_post_workout_carbohydrate_g == 80.0
    assert section.fueling_post_workout_protein_g == 24.0
    assert not hasattr(section, "energy_balance")


def test_body_composition_profile_and_trend_are_mapped_without_classification():
    section = _build(body_composition=_body_composition()).body_composition

    assert section.current_body_mass_kg == 80.0
    assert section.body_fat_percent == 17.0
    assert section.muscle_mass_kg == 61.0
    assert section.body_water_percent == 55.0
    assert section.visceral_fat_rating is None
    assert section.basal_metabolic_rate_kcal == 1750.0
    assert section.waist_circumference_cm == 82.0
    assert section.trend_baseline_body_mass_kg == 81.5
    assert section.trend_period_days == 28
    assert section.trend_absolute_change_kg == -1.5
    assert section.trend_percentage_change == -1.84


def test_goal_maps_configuration_without_progress_or_action():
    section = _build(goal=_goal()).goal

    assert section.goal_type == "reduce_body_mass"
    assert section.target_body_mass_kg == 77.0
    assert section.valid_from == date(2026, 7, 1)
    assert section.valid_until == date(2026, 10, 1)
    assert not hasattr(section, "progress")
    assert not hasattr(section, "recommended_action")


@pytest.mark.parametrize(
    ("source_name", "source", "section_name"),
    (
        (
            "nutrition",
            _nutrition(NutritionDataStatus.PARTIAL),
            "nutrition",
        ),
        (
            "body_composition",
            _body_composition(BodyCompositionDataStatus.PARTIAL),
            "body_composition",
        ),
        (
            "goal",
            _goal(GoalAssessmentDataStatus.PARTIAL),
            "goal",
        ),
    ),
)
def test_partial_assessment_preserves_completeness_evidence_and_limitations(
    source_name,
    source,
    section_name,
):
    section = getattr(_build(**{source_name: source}), section_name)

    assert section.metadata.status is DashboardSectionStatus.PARTIAL
    assert section.metadata.completeness_score == source.confidence
    assert section.metadata.evidence == tuple(sorted(set(source.evidence)))
    assert section.metadata.limitations == tuple(
        dict.fromkeys(source.limitations)
    )


@pytest.mark.parametrize(
    ("source_name", "source", "section_name"),
    (
        (
            "nutrition",
            _nutrition(NutritionDataStatus.INSUFFICIENT_DATA),
            "nutrition",
        ),
        (
            "body_composition",
            _body_composition(BodyCompositionDataStatus.INSUFFICIENT_DATA),
            "body_composition",
        ),
        (
            "goal",
            _goal(GoalAssessmentDataStatus.INSUFFICIENT_DATA),
            "goal",
        ),
    ),
)
def test_insufficient_assessment_is_unavailable_without_losing_source_score(
    source_name,
    source,
    section_name,
):
    section = getattr(_build(**{source_name: source}), section_name)

    assert section.metadata.status is DashboardSectionStatus.UNAVAILABLE
    assert section.metadata.completeness_score == source.confidence


def test_all_missing_sources_produce_required_unavailable_typed_sections():
    dashboard = _build()
    sections = (
        dashboard.health,
        dashboard.recovery,
        dashboard.performance,
        dashboard.training,
        dashboard.nutrition,
        dashboard.body_composition,
        dashboard.goal,
        dashboard.recommendations,
        dashboard.data_quality,
    )

    assert all(
        section.metadata.status is DashboardSectionStatus.UNAVAILABLE
        for section in sections
    )
    assert all(
        section.metadata.completeness_score is None
        for section in sections
    )
    assert dashboard.health.hrv_ms is None
    assert dashboard.recovery.recovery_score is None
    assert dashboard.performance.weekly_training_load_tss is None
    assert dashboard.training.estimated_duration_minutes is None
    assert dashboard.nutrition.observed_daily_expenditure_kcal is None
    assert dashboard.body_composition.current_body_mass_kg is None
    assert dashboard.goal.goal_type is None
    assert dashboard.recommendations.items == ()


def test_rest_day_decision_is_a_ready_training_result_without_planned_workout():
    decision = _decision(objective=TrainingObjective.REST)

    section = _build(decision=decision).training

    assert section.metadata.status is DashboardSectionStatus.READY
    assert section.metadata.completeness_score is None
    assert section.workout_goal == "REST"
    assert section.workout_name is None
    assert section.estimated_duration_minutes == decision.duration
    assert section.target_tss == decision.target_tss


def test_empty_recommendation_result_is_ready_while_missing_result_is_unavailable():
    empty = _build(
        recommendation_result=RecommendationResult((), AS_OF),
        explainability=_explainability(()),
    ).recommendations
    missing = _build().recommendations

    assert empty.metadata.status is DashboardSectionStatus.READY
    assert empty.metadata.completeness_score is None
    assert empty.items == ()
    assert missing.metadata.status is DashboardSectionStatus.UNAVAILABLE
    assert missing.items == ()


@pytest.mark.parametrize(
    ("recommendation_result", "explainability"),
    (
        (_recommendation_result(), _explainability(("only one",))),
        (None, _explainability(("orphan message",))),
    ),
)
def test_recommendation_and_explainability_length_mismatch_is_rejected(
    recommendation_result,
    explainability,
):
    with pytest.raises(ValueError, match="must have equal length"):
        _build(
            recommendation_result=recommendation_result,
            explainability=explainability,
        )


def test_recommendations_preserve_builder_order_and_positional_messages():
    section = _build(
        recommendation_result=_recommendation_result(),
        explainability=_explainability(),
    ).recommendations

    assert tuple(item.id for item in section.items) == ("hydration", "sleep")
    assert tuple(item.message for item in section.items) == (
        "Increase hydration.",
        "Extend sleep duration.",
    )
    first = section.items[0]
    assert first.recommendation_type == "increase_hydration"
    assert first.priority == "medium"
    assert first.source_confidence == 0.8
    assert first.evidence == ("water:a", "water:b")
    assert first.source_rules == ("RuleB", "RuleA")
    assert first.as_of == AS_OF


def test_data_quality_aggregates_only_existing_source_metadata_deterministically():
    body = _body_composition(
        limitations=("shared", "body_only", "shared"),
    )
    nutrition = _nutrition(
        limitations=("shared", "nutrition_only"),
    )
    goal = _goal(limitations=("goal_only",))
    trend = _trend_quality(limitations=("trend_only", "shared"))

    section = _build(
        body_composition=body,
        nutrition=nutrition,
        goal=goal,
        body_mass_trend_quality=trend,
    ).data_quality

    assert section.metadata.status is DashboardSectionStatus.READY
    assert section.metadata.completeness_score is None
    assert section.body_composition_status == "complete"
    assert section.nutrition_status == "complete"
    assert section.goal_status == "complete"
    assert section.trend_quality_status == "partial"
    assert section.global_limitations == (
        "shared",
        "body_only",
        "nutrition_only",
        "goal_only",
        "trend_only",
    )
    assert section.metadata.limitations == section.global_limitations
    assert section.metadata.evidence == (
        "body:a",
        "body:b",
        "goal:a",
        "goal:b",
        "nutrition:a",
        "nutrition:b",
        "trend:a",
        "trend:b",
    )


def test_partial_data_quality_means_some_quality_sources_are_missing():
    section = _build(nutrition=_nutrition()).data_quality

    assert section.metadata.status is DashboardSectionStatus.PARTIAL
    assert section.nutrition_status == "complete"
    assert section.body_composition_status is None
    assert section.goal_status is None
    assert section.trend_quality_status is None


def test_missing_values_remain_none_without_zero_fallback():
    nutrition = _nutrition()
    body = _body_composition()
    section = _build(
        nutrition=nutrition,
        body_composition=body,
    )

    assert section.nutrition.estimated_daily_requirement_kcal is None
    assert section.body_composition.visceral_fat_rating is None
    assert section.training.target_if is None


def test_two_equal_calls_are_deterministic_fresh_and_do_not_mutate_inputs():
    engine = DashboardEngine()
    inputs = _full_inputs()
    before = deepcopy(inputs)

    first = engine.build(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        **inputs,
    )
    second = engine.build(
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
        **inputs,
    )

    assert first == second
    assert first is not second
    assert first.health is not second.health
    assert inputs == before
    assert vars(engine) == {}


def test_historical_source_as_of_is_allowed_without_requiring_exact_match():
    historical = AS_OF - timedelta(hours=1)
    result = _build(nutrition=_nutrition(as_of=historical))

    assert result.nutrition.metadata.status is DashboardSectionStatus.READY
    assert result.as_of == AS_OF


@pytest.mark.parametrize(
    ("valid_for_date", "as_of", "error", "message"),
    (
        (datetime(2026, 8, 3), AS_OF, TypeError, "must be a date"),
        (VALID_FOR_DATE, VALID_FOR_DATE, TypeError, "must be a datetime"),
        (date(2026, 8, 4), AS_OF, ValueError, "cannot be after as_of"),
    ),
)
def test_top_level_temporal_contract_is_validated(
    valid_for_date,
    as_of,
    error,
    message,
):
    with pytest.raises(error, match=message):
        _build(valid_for_date=valid_for_date, as_of=as_of)


def test_mixed_naive_and_aware_source_timestamps_are_rejected():
    aware_as_of = AS_OF.replace(tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="compatible timezones"):
        _build(as_of=aware_as_of, nutrition=_nutrition(as_of=AS_OF))


def test_consistently_aware_top_level_and_source_timestamps_are_accepted():
    aware_as_of = AS_OF.replace(tzinfo=timezone.utc)

    result = _build(
        as_of=aware_as_of,
        nutrition=_nutrition(as_of=aware_as_of),
    )

    assert result.as_of == aware_as_of


def test_source_timestamp_after_dashboard_as_of_is_rejected():
    with pytest.raises(ValueError, match="cannot be after dashboard as_of"):
        _build(nutrition=_nutrition(as_of=AS_OF + timedelta(minutes=1)))


def test_source_valid_for_date_after_dashboard_date_is_rejected():
    future = replace(_nutrition(), valid_for_date=date(2026, 8, 4))

    with pytest.raises(ValueError, match="cannot be after dashboard date"):
        _build(nutrition=future)


def test_health_date_after_dashboard_date_is_rejected():
    future_health = replace(_health(), date=date(2026, 8, 4))

    with pytest.raises(ValueError, match="health date"):
        _build(health=future_health)


def test_dashboard_engine_is_publicly_importable():
    import dashboard
    from dashboard.engine import DashboardEngine as Implementation

    assert dashboard.DashboardEngine is Implementation
