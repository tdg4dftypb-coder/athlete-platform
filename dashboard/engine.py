from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from adaptive.models import (
    GoalAssessmentDataStatus,
)
from body_composition.models import BodyCompositionDataStatus
from dashboard.models import (
    DASHBOARD_CONTRACT_VERSION,
    AthleteDashboard,
    DashboardBodyCompositionSection,
    DashboardDataQualitySection,
    DashboardGoalSection,
    DashboardHealthSection,
    DashboardNutritionSection,
    DashboardPerformanceSection,
    DashboardRecommendationItem,
    DashboardRecommendationsSection,
    DashboardRecoverySection,
    DashboardSectionMetadata,
    DashboardSectionStatus,
    DashboardTrainingSection,
)
from nutrition.models import NutritionDataStatus

if TYPE_CHECKING:
    from adaptive.models import BodyMassTrendQuality, GoalAssessment
    from application.decision_explainability import ExplainabilityResult
    from body_composition.models import BodyCompositionAssessment, BodyMeasurement
    from core.models import HealthDaily
    from decision.models import DecisionResult
    from nutrition.models import NutritionAssessment
    from performance.models import PerformanceState
    from planner.models import PlannedWorkout
    from recommendation.models import RecommendationResult
    from recovery.models import RecoveryResult


class DashboardEngine:
    """Assemble canonical results into a presentation read-side projection."""

    def build(
        self,
        *,
        valid_for_date: date,
        as_of: datetime,
        health: HealthDaily | None,
        recovery: RecoveryResult | None,
        performance: PerformanceState | None,
        decision: DecisionResult | None,
        planned_workout: PlannedWorkout | None,
        nutrition: NutritionAssessment | None,
        body_composition: BodyCompositionAssessment | None,
        body_mass_trend_quality: BodyMassTrendQuality | None,
        goal: GoalAssessment | None,
        recommendation_result: RecommendationResult | None,
        explainability: ExplainabilityResult | None,
    ) -> AthleteDashboard:
        self._validate_temporal_contract(
            valid_for_date=valid_for_date,
            as_of=as_of,
            health=health,
            nutrition=nutrition,
            body_composition=body_composition,
            body_mass_trend_quality=body_mass_trend_quality,
            goal=goal,
            recommendation_result=recommendation_result,
        )

        return AthleteDashboard(
            contract_version=DASHBOARD_CONTRACT_VERSION,
            valid_for_date=valid_for_date,
            as_of=as_of,
            health=self._health_section(health),
            recovery=self._recovery_section(recovery),
            performance=self._performance_section(performance),
            training=self._training_section(decision, planned_workout),
            nutrition=self._nutrition_section(nutrition),
            body_composition=self._body_composition_section(body_composition),
            goal=self._goal_section(goal),
            recommendations=self._recommendations_section(
                recommendation_result,
                explainability,
            ),
            data_quality=self._data_quality_section(
                body_composition,
                nutrition,
                goal,
                body_mass_trend_quality,
            ),
        )

    @classmethod
    def _health_section(
        cls,
        health: HealthDaily | None,
    ) -> DashboardHealthSection:
        if health is None:
            return DashboardHealthSection(
                metadata=cls._unavailable_metadata(),
                hrv_ms=None,
                resting_heart_rate_bpm=None,
                sleep_minutes=None,
                steps=None,
                active_energy_kcal=None,
                resting_energy_kcal=None,
                respiratory_rate_per_minute=None,
                oxygen_saturation_percent=None,
                wrist_temperature_celsius=None,
            )

        return DashboardHealthSection(
            metadata=cls._ready_metadata(),
            hrv_ms=health.hrv,
            resting_heart_rate_bpm=health.resting_hr,
            sleep_minutes=health.sleep_duration,
            steps=health.steps,
            active_energy_kcal=health.active_energy,
            resting_energy_kcal=health.resting_energy,
            respiratory_rate_per_minute=health.respiratory_rate,
            oxygen_saturation_percent=health.spo2,
            wrist_temperature_celsius=health.wrist_temperature,
        )

    @classmethod
    def _recovery_section(
        cls,
        recovery: RecoveryResult | None,
    ) -> DashboardRecoverySection:
        if recovery is None:
            return DashboardRecoverySection(
                metadata=cls._unavailable_metadata(),
                recovery_score=None,
                sleep_score=None,
            )

        return DashboardRecoverySection(
            metadata=cls._ready_metadata(),
            recovery_score=recovery.score,
            sleep_score=recovery.sleep.score,
        )

    @classmethod
    def _performance_section(
        cls,
        performance: PerformanceState | None,
    ) -> DashboardPerformanceSection:
        if performance is None:
            return DashboardPerformanceSection(
                metadata=cls._unavailable_metadata(),
                weekly_training_load_tss=None,
                monthly_training_load_tss=None,
                fatigue_tss_per_day=None,
                fitness_tss_per_day=None,
                form_tss_per_day=None,
            )

        return DashboardPerformanceSection(
            metadata=cls._ready_metadata(),
            weekly_training_load_tss=performance.weekly.total_tss,
            monthly_training_load_tss=performance.monthly.total_tss,
            fatigue_tss_per_day=performance.fatigue,
            fitness_tss_per_day=performance.fitness,
            form_tss_per_day=performance.freshness,
        )

    @classmethod
    def _training_section(
        cls,
        decision: DecisionResult | None,
        planned_workout: PlannedWorkout | None,
    ) -> DashboardTrainingSection:
        if decision is None:
            return DashboardTrainingSection(
                metadata=cls._unavailable_metadata(),
                workout_name=None,
                workout_goal=None,
                estimated_duration_minutes=None,
                target_tss=None,
                target_if=None,
                decision_action=None,
                decision_reasons=(),
            )

        return DashboardTrainingSection(
            metadata=cls._ready_metadata(),
            workout_name=(
                planned_workout.name if planned_workout is not None else None
            ),
            workout_goal=(
                decision.objective.value
                if decision.objective is not None
                else None
            ),
            estimated_duration_minutes=(
                planned_workout.estimated_duration
                if planned_workout is not None
                else decision.duration
            ),
            target_tss=(
                planned_workout.target_tss
                if planned_workout is not None
                else decision.target_tss
            ),
            target_if=None,
            decision_action=decision.recommendation.value,
            decision_reasons=tuple(
                reason.value for reason in decision.decision_reasons
            ),
        )

    @classmethod
    def _nutrition_section(
        cls,
        assessment: NutritionAssessment | None,
    ) -> DashboardNutritionSection:
        if assessment is None:
            return DashboardNutritionSection(
                metadata=cls._unavailable_metadata(),
                observed_daily_expenditure_kcal=None,
                estimated_daily_requirement_kcal=None,
                carbohydrate_target_g=None,
                protein_target_g=None,
                carbohydrate_target_g_per_kg=None,
                protein_target_g_per_kg=None,
                hydration_daily_ml=None,
                hydration_during_workout_ml_per_hour=None,
                fueling_pre_workout_carbohydrate_g=None,
                fueling_during_workout_carbohydrate_g_per_hour=None,
                fueling_post_workout_carbohydrate_g=None,
                fueling_post_workout_protein_g=None,
            )

        energy = assessment.energy_requirement
        macros = assessment.macro_targets
        hydration = assessment.hydration_target
        fueling = assessment.fueling_plan
        return DashboardNutritionSection(
            metadata=cls._assessment_metadata(
                cls._nutrition_status(assessment.data_status),
                assessment.confidence,
                assessment.evidence,
                assessment.limitations,
            ),
            observed_daily_expenditure_kcal=(
                energy.observed_daily_expenditure_kcal
            ),
            estimated_daily_requirement_kcal=(
                energy.estimated_daily_requirement_kcal
            ),
            carbohydrate_target_g=macros.carbohydrate_g,
            protein_target_g=macros.protein_g,
            carbohydrate_target_g_per_kg=macros.carbohydrate_g_per_kg,
            protein_target_g_per_kg=macros.protein_g_per_kg,
            hydration_daily_ml=hydration.daily_ml,
            hydration_during_workout_ml_per_hour=(
                hydration.during_workout_ml_per_hour
            ),
            fueling_pre_workout_carbohydrate_g=(
                fueling.pre_workout_carbohydrate_g
            ),
            fueling_during_workout_carbohydrate_g_per_hour=(
                fueling.during_workout_carbohydrate_g_per_hour
            ),
            fueling_post_workout_carbohydrate_g=(
                fueling.post_workout_carbohydrate_g
            ),
            fueling_post_workout_protein_g=(
                fueling.post_workout_protein_g
            ),
        )

    @classmethod
    def _body_composition_section(
        cls,
        assessment: BodyCompositionAssessment | None,
    ) -> DashboardBodyCompositionSection:
        if assessment is None:
            return DashboardBodyCompositionSection(
                metadata=cls._unavailable_metadata(),
                current_body_mass_kg=None,
                body_fat_percent=None,
                muscle_mass_kg=None,
                body_water_percent=None,
                visceral_fat_rating=None,
                basal_metabolic_rate_kcal=None,
                waist_circumference_cm=None,
                trend_baseline_body_mass_kg=None,
                trend_period_days=None,
                trend_absolute_change_kg=None,
                trend_percentage_change=None,
            )

        profile = assessment.profile
        trend = assessment.body_mass_trend
        return DashboardBodyCompositionSection(
            metadata=cls._assessment_metadata(
                cls._body_composition_status(assessment.data_status),
                assessment.confidence,
                assessment.evidence,
                assessment.limitations,
            ),
            current_body_mass_kg=cls._measurement_value(profile.body_mass),
            body_fat_percent=cls._measurement_value(profile.body_fat),
            muscle_mass_kg=cls._measurement_value(profile.muscle_mass),
            body_water_percent=cls._measurement_value(profile.body_water),
            visceral_fat_rating=cls._measurement_value(profile.visceral_fat),
            basal_metabolic_rate_kcal=cls._measurement_value(
                profile.basal_metabolic_rate
            ),
            waist_circumference_cm=cls._measurement_value(
                profile.waist_circumference
            ),
            trend_baseline_body_mass_kg=(
                trend.baseline.value if trend is not None else None
            ),
            trend_period_days=(trend.period_days if trend is not None else None),
            trend_absolute_change_kg=(
                trend.absolute_change_kg if trend is not None else None
            ),
            trend_percentage_change=(
                trend.percentage_change if trend is not None else None
            ),
        )

    @classmethod
    def _goal_section(
        cls,
        assessment: GoalAssessment | None,
    ) -> DashboardGoalSection:
        if assessment is None:
            return DashboardGoalSection(
                metadata=cls._unavailable_metadata(),
                goal_type=None,
                target_body_mass_kg=None,
                valid_from=None,
                valid_until=None,
            )

        goal = assessment.goal
        return DashboardGoalSection(
            metadata=cls._assessment_metadata(
                cls._goal_status(assessment.data_status),
                assessment.confidence,
                assessment.evidence,
                assessment.limitations,
            ),
            goal_type=goal.goal_type.value if goal is not None else None,
            target_body_mass_kg=(
                goal.target_body_mass_kg if goal is not None else None
            ),
            valid_from=goal.valid_from if goal is not None else None,
            valid_until=goal.valid_until if goal is not None else None,
        )

    @classmethod
    def _recommendations_section(
        cls,
        recommendation_result: RecommendationResult | None,
        explainability: ExplainabilityResult | None,
    ) -> DashboardRecommendationsSection:
        messages = (
            explainability.recommendations
            if explainability is not None
            else ()
        )
        if recommendation_result is None:
            if messages:
                raise ValueError(
                    "recommendations and explainability messages must have "
                    "equal length"
                )
            return DashboardRecommendationsSection(
                metadata=cls._unavailable_metadata(),
                items=(),
            )

        recommendations = recommendation_result.recommendations
        if len(recommendations) != len(messages):
            raise ValueError(
                "recommendations and explainability messages must have equal "
                "length"
            )

        items = tuple(
            DashboardRecommendationItem(
                id=recommendation.id,
                recommendation_type=recommendation.type.value,
                priority=recommendation.priority.value,
                source_confidence=recommendation.confidence,
                message=message,
                evidence=cls._sorted_unique(recommendation.evidence),
                source_rules=cls._stable_unique(recommendation.source_rules),
                as_of=recommendation.as_of,
            )
            for recommendation, message in zip(recommendations, messages)
        )
        evidence = cls._sorted_unique(
            tuple(
                evidence_item
                for recommendation in recommendations
                for evidence_item in recommendation.evidence
            )
        )
        return DashboardRecommendationsSection(
            metadata=DashboardSectionMetadata(
                status=DashboardSectionStatus.READY,
                completeness_score=None,
                evidence=evidence,
            ),
            items=items,
        )

    @classmethod
    def _data_quality_section(
        cls,
        body_composition: BodyCompositionAssessment | None,
        nutrition: NutritionAssessment | None,
        goal: GoalAssessment | None,
        trend_quality: BodyMassTrendQuality | None,
    ) -> DashboardDataQualitySection:
        sources = (body_composition, nutrition, goal, trend_quality)
        available_count = sum(source is not None for source in sources)
        if available_count == 0:
            status = DashboardSectionStatus.UNAVAILABLE
        elif available_count == len(sources):
            status = DashboardSectionStatus.READY
        else:
            status = DashboardSectionStatus.PARTIAL

        limitations = cls._stable_unique(
            tuple(
                limitation
                for source in sources
                if source is not None
                for limitation in source.limitations
            )
        )
        evidence = cls._sorted_unique(
            tuple(
                evidence_item
                for source in sources
                if source is not None
                for evidence_item in source.evidence
            )
        )
        return DashboardDataQualitySection(
            metadata=DashboardSectionMetadata(
                status=status,
                completeness_score=None,
                limitations=limitations,
                evidence=evidence,
            ),
            body_composition_status=(
                body_composition.data_status.value
                if body_composition is not None
                else None
            ),
            nutrition_status=(
                nutrition.data_status.value if nutrition is not None else None
            ),
            goal_status=goal.data_status.value if goal is not None else None,
            trend_quality_status=(
                trend_quality.data_status.value
                if trend_quality is not None
                else None
            ),
            global_limitations=limitations,
        )

    @classmethod
    def _validate_temporal_contract(
        cls,
        *,
        valid_for_date: date,
        as_of: datetime,
        health: HealthDaily | None,
        nutrition: NutritionAssessment | None,
        body_composition: BodyCompositionAssessment | None,
        body_mass_trend_quality: BodyMassTrendQuality | None,
        goal: GoalAssessment | None,
        recommendation_result: RecommendationResult | None,
    ) -> None:
        if isinstance(valid_for_date, datetime) or not isinstance(
            valid_for_date,
            date,
        ):
            raise TypeError("valid_for_date must be a date")
        if not isinstance(as_of, datetime):
            raise TypeError("as_of must be a datetime")
        if valid_for_date > as_of.date():
            raise ValueError("valid_for_date cannot be after as_of")
        if health is not None and health.date > valid_for_date:
            raise ValueError("health date cannot be after dashboard date")

        dated_sources = (
            ("nutrition", nutrition),
            ("body_composition", body_composition),
            ("body_mass_trend_quality", body_mass_trend_quality),
            ("goal", goal),
        )
        for name, source in dated_sources:
            if source is None:
                continue
            if source.valid_for_date > valid_for_date:
                raise ValueError(
                    f"{name} valid_for_date cannot be after dashboard date"
                )
            cls._validate_source_timestamp(f"{name} as_of", source.as_of, as_of)

        if body_composition is not None:
            profile = body_composition.profile
            measurements = (
                profile.body_mass,
                profile.body_fat,
                profile.muscle_mass,
                profile.body_water,
                profile.visceral_fat,
                profile.basal_metabolic_rate,
                profile.waist_circumference,
            )
            for measurement in measurements:
                if measurement is not None:
                    cls._validate_source_timestamp(
                        "body measurement observed_at",
                        measurement.observed_at,
                        as_of,
                    )
            if body_composition.body_mass_trend is not None:
                cls._validate_source_timestamp(
                    "body trend current observed_at",
                    body_composition.body_mass_trend.current.observed_at,
                    as_of,
                )
                cls._validate_source_timestamp(
                    "body trend baseline observed_at",
                    body_composition.body_mass_trend.baseline.observed_at,
                    as_of,
                )

        if goal is not None and goal.goal is not None:
            cls._validate_source_timestamp(
                "goal recorded_at",
                goal.goal.recorded_at,
                as_of,
            )

        if recommendation_result is not None:
            if recommendation_result.as_of is not None:
                cls._validate_source_timestamp(
                    "recommendation result as_of",
                    recommendation_result.as_of,
                    as_of,
                )
            for recommendation in recommendation_result.recommendations:
                cls._validate_source_timestamp(
                    "recommendation as_of",
                    recommendation.as_of,
                    as_of,
                )

    @staticmethod
    def _validate_source_timestamp(
        name: str,
        value: datetime,
        as_of: datetime,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(f"{name} must be a datetime")
        value_is_aware = value.tzinfo is not None and value.utcoffset() is not None
        as_of_is_aware = as_of.tzinfo is not None and as_of.utcoffset() is not None
        if value_is_aware != as_of_is_aware:
            raise ValueError(
                f"{name} and dashboard as_of must use compatible timezones"
            )
        if value > as_of:
            raise ValueError(f"{name} cannot be after dashboard as_of")

    @staticmethod
    def _body_composition_status(
        status: BodyCompositionDataStatus,
    ) -> DashboardSectionStatus:
        return {
            BodyCompositionDataStatus.COMPLETE: DashboardSectionStatus.READY,
            BodyCompositionDataStatus.PARTIAL: DashboardSectionStatus.PARTIAL,
            BodyCompositionDataStatus.INSUFFICIENT_DATA: (
                DashboardSectionStatus.UNAVAILABLE
            ),
        }[status]

    @staticmethod
    def _nutrition_status(
        status: NutritionDataStatus,
    ) -> DashboardSectionStatus:
        return {
            NutritionDataStatus.COMPLETE: DashboardSectionStatus.READY,
            NutritionDataStatus.PARTIAL: DashboardSectionStatus.PARTIAL,
            NutritionDataStatus.INSUFFICIENT_DATA: (
                DashboardSectionStatus.UNAVAILABLE
            ),
        }[status]

    @staticmethod
    def _goal_status(
        status: GoalAssessmentDataStatus,
    ) -> DashboardSectionStatus:
        return {
            GoalAssessmentDataStatus.COMPLETE: DashboardSectionStatus.READY,
            GoalAssessmentDataStatus.PARTIAL: DashboardSectionStatus.PARTIAL,
            GoalAssessmentDataStatus.INSUFFICIENT_DATA: (
                DashboardSectionStatus.UNAVAILABLE
            ),
        }[status]

    @classmethod
    def _assessment_metadata(
        cls,
        status: DashboardSectionStatus,
        completeness_score: float,
        evidence: tuple[str, ...],
        limitations: tuple[str, ...],
    ) -> DashboardSectionMetadata:
        return DashboardSectionMetadata(
            status=status,
            completeness_score=completeness_score,
            limitations=cls._stable_unique(limitations),
            evidence=cls._sorted_unique(evidence),
        )

    @staticmethod
    def _ready_metadata() -> DashboardSectionMetadata:
        return DashboardSectionMetadata(
            status=DashboardSectionStatus.READY,
            completeness_score=None,
        )

    @staticmethod
    def _unavailable_metadata() -> DashboardSectionMetadata:
        return DashboardSectionMetadata(
            status=DashboardSectionStatus.UNAVAILABLE,
            completeness_score=None,
        )

    @staticmethod
    def _measurement_value(
        measurement: BodyMeasurement | None,
    ) -> float | None:
        return measurement.value if measurement is not None else None

    @staticmethod
    def _sorted_unique(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(values)))

    @staticmethod
    def _stable_unique(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))
