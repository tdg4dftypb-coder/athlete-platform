from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from math import isfinite

from nutrition.models import (
    EnergyRequirement,
    FuelingPlan,
    HydrationTarget,
    MacroTargets,
    NutritionAssessment,
    NutritionDataStatus,
    NutritionInput,
)


class _TrainingDemand(Enum):
    UNKNOWN = "unknown"
    REST = "rest"
    RECOVERY = "recovery"
    ENDURANCE = "endurance"
    TEMPO = "tempo"
    HIGH = "high"


@dataclass(frozen=True)
class _NutritionPolicy:
    """Deterministic v1 targets, not physiological or clinical constants."""

    body_mass_max_age: timedelta = timedelta(days=30)
    protein_g_per_kg: float = 1.6
    daily_hydration_ml_per_kg: float = 35.0
    pre_workout_hydration_ml_per_kg: float = 5.0
    post_workout_protein_g_per_kg: float = 0.3
    high_training_tss: float = 90.0
    short_workout_max_duration_min: int = 45
    long_workout_min_duration_min: int = 120
    pre_workout_window_min: int = 120
    post_workout_window_min: int = 60
    short_workout_carbohydrate_g_per_hour: float = 0.0
    endurance_carbohydrate_g_per_hour: float = 30.0
    tempo_carbohydrate_g_per_hour: float = 45.0
    high_carbohydrate_g_per_hour: float = 60.0


_POLICY_V1 = _NutritionPolicy()

_CARBOHYDRATE_G_PER_KG = {
    _TrainingDemand.REST: 3.0,
    _TrainingDemand.RECOVERY: 3.5,
    _TrainingDemand.ENDURANCE: 4.5,
    _TrainingDemand.TEMPO: 5.0,
    _TrainingDemand.HIGH: 6.0,
}

_PRE_WORKOUT_CARBOHYDRATE_G = {
    _TrainingDemand.RECOVERY: 20.0,
    _TrainingDemand.ENDURANCE: 40.0,
    _TrainingDemand.TEMPO: 60.0,
    _TrainingDemand.HIGH: 75.0,
}

_POST_WORKOUT_CARBOHYDRATE_G_PER_KG = {
    _TrainingDemand.RECOVERY: 0.5,
    _TrainingDemand.ENDURANCE: 0.8,
    _TrainingDemand.TEMPO: 1.0,
    _TrainingDemand.HIGH: 1.0,
}

_WORKOUT_HYDRATION_ML_PER_HOUR = {
    _TrainingDemand.RECOVERY: 400.0,
    _TrainingDemand.ENDURANCE: 500.0,
    _TrainingDemand.TEMPO: 550.0,
    _TrainingDemand.HIGH: 600.0,
}


class NutritionEngine:
    """Build a deterministic nutrition assessment from normalized facts.

    COMPLETE requires usable observed energy, carbohydrate and protein macro
    targets, an applicable fueling plan, and daily plus applicable workout
    hydration targets. Each complete section contributes 0.25 to confidence;
    a partially usable section contributes 0.125. Confidence measures only
    assessment completeness, never accuracy or source quality.
    """

    def analyze(self, nutrition_input: NutritionInput) -> NutritionAssessment:
        self._validate(nutrition_input)

        fresh_body_mass = self._fresh_body_mass(nutrition_input)
        training_demand = self._classify_training_demand(nutrition_input)

        energy, energy_score, energy_limitations = self._build_energy(
            nutrition_input
        )
        macros, macro_score, macro_limitations = self._build_macros(
            fresh_body_mass,
            training_demand,
        )
        fueling, fueling_score, fueling_limitations = self._build_fueling(
            nutrition_input,
            fresh_body_mass,
            training_demand,
        )
        hydration, hydration_score, hydration_limitations = (
            self._build_hydration(
                nutrition_input,
                fresh_body_mass,
                training_demand,
            )
        )

        confidence = (
            energy_score + macro_score + fueling_score + hydration_score
        )
        if confidence == 1.0:
            data_status = NutritionDataStatus.COMPLETE
        elif confidence > 0.0:
            data_status = NutritionDataStatus.PARTIAL
        else:
            data_status = NutritionDataStatus.INSUFFICIENT_DATA

        limitations = self._stable_unique(
            energy_limitations
            + macro_limitations
            + fueling_limitations
            + hydration_limitations
            + ("missing_energy_intake",)
        )

        return NutritionAssessment(
            energy_requirement=energy,
            macro_targets=macros,
            fueling_plan=fueling,
            hydration_target=hydration,
            data_status=data_status,
            confidence=confidence,
            evidence=tuple(sorted(set(nutrition_input.evidence))),
            limitations=limitations,
            valid_for_date=nutrition_input.valid_for_date,
            as_of=nutrition_input.as_of,
        )

    @staticmethod
    def _build_energy(
        nutrition_input: NutritionInput,
    ) -> tuple[EnergyRequirement, float, tuple[str, ...]]:
        resting_energy = nutrition_input.resting_energy_kcal
        active_energy = nutrition_input.active_energy_kcal
        has_resting_energy = resting_energy is not None
        has_active_energy = active_energy is not None
        has_energy_date = nutrition_input.energy_observed_for_date is not None

        if (
            resting_energy is not None
            and active_energy is not None
            and has_energy_date
        ):
            observed_expenditure = resting_energy + active_energy
            score = 0.25
        elif has_resting_energy or has_active_energy:
            observed_expenditure = None
            score = 0.125
        else:
            observed_expenditure = None
            score = 0.0

        limitations = tuple(
            limitation
            for missing, limitation in (
                (
                    not has_resting_energy,
                    "missing_resting_energy_kcal",
                ),
                (
                    not has_active_energy,
                    "missing_active_energy_kcal",
                ),
                (
                    not has_energy_date,
                    "missing_energy_observed_for_date",
                ),
            )
            if missing
        ) + ("missing_estimated_daily_requirement",)

        return (
            EnergyRequirement(
                estimated_daily_requirement_kcal=None,
                observed_daily_expenditure_kcal=observed_expenditure,
                resting_energy_kcal=resting_energy,
                active_energy_kcal=active_energy,
            ),
            score,
            limitations,
        )

    @staticmethod
    def _build_macros(
        body_mass_kg: float | None,
        training_demand: _TrainingDemand,
    ) -> tuple[MacroTargets, float, tuple[str, ...]]:
        limitations: tuple[str, ...] = ("fat_target_unavailable",)
        if body_mass_kg is None:
            return (
                MacroTargets(),
                0.0,
                ("missing_fresh_body_mass", "missing_macro_targets")
                + limitations,
            )

        protein_per_kg = _POLICY_V1.protein_g_per_kg
        protein_g = round(body_mass_kg * protein_per_kg, 1)
        if training_demand is _TrainingDemand.UNKNOWN:
            return (
                MacroTargets(
                    protein_g=protein_g,
                    protein_g_per_kg=protein_per_kg,
                ),
                0.125,
                (
                    "missing_training_demand",
                    "missing_macro_targets",
                )
                + limitations,
            )

        carbohydrate_per_kg = _CARBOHYDRATE_G_PER_KG[training_demand]
        return (
            MacroTargets(
                carbohydrate_g=round(body_mass_kg * carbohydrate_per_kg, 1),
                protein_g=protein_g,
                fat_g=None,
                carbohydrate_g_per_kg=carbohydrate_per_kg,
                protein_g_per_kg=protein_per_kg,
                fat_g_per_kg=None,
            ),
            0.25,
            limitations,
        )

    @classmethod
    def _build_fueling(
        cls,
        nutrition_input: NutritionInput,
        body_mass_kg: float | None,
        training_demand: _TrainingDemand,
    ) -> tuple[FuelingPlan, float, tuple[str, ...]]:
        if training_demand is _TrainingDemand.UNKNOWN:
            return (
                FuelingPlan(),
                0.0,
                ("missing_training_plan", "missing_fueling_plan"),
            )
        if training_demand is _TrainingDemand.REST:
            return FuelingPlan(), 0.25, ()

        duration = nutrition_input.planned_duration_min
        during_carbohydrate = None
        score = 0.125
        limitations: tuple[str, ...] = (
            "missing_planned_duration",
            "missing_fueling_plan",
        )
        if duration is not None:
            during_carbohydrate = cls._during_carbohydrate_rate(
                duration,
                training_demand,
            )
            score = 0.25
            limitations = ()

        post_carbohydrate = None
        post_protein = None
        if body_mass_kg is not None:
            post_carbohydrate = round(
                body_mass_kg
                * _POST_WORKOUT_CARBOHYDRATE_G_PER_KG[training_demand],
                1,
            )
            post_protein = round(
                body_mass_kg
                * _POLICY_V1.post_workout_protein_g_per_kg,
                1,
            )

        return (
            FuelingPlan(
                pre_workout_carbohydrate_g=(
                    _PRE_WORKOUT_CARBOHYDRATE_G[training_demand]
                ),
                during_workout_carbohydrate_g_per_hour=during_carbohydrate,
                post_workout_carbohydrate_g=post_carbohydrate,
                post_workout_protein_g=post_protein,
                pre_workout_window_min=_POLICY_V1.pre_workout_window_min,
                post_workout_window_min=_POLICY_V1.post_workout_window_min,
            ),
            score,
            limitations,
        )

    @staticmethod
    def _build_hydration(
        nutrition_input: NutritionInput,
        body_mass_kg: float | None,
        training_demand: _TrainingDemand,
    ) -> tuple[HydrationTarget, float, tuple[str, ...]]:
        limitations: tuple[str, ...] = ()
        has_training = training_demand not in (
            _TrainingDemand.UNKNOWN,
            _TrainingDemand.REST,
        )

        daily_ml = None
        daily_ml_per_kg = None
        pre_workout_ml = None
        if body_mass_kg is not None:
            daily_ml_per_kg = _POLICY_V1.daily_hydration_ml_per_kg
            daily_ml = round(body_mass_kg * daily_ml_per_kg, 1)
            if has_training:
                pre_workout_ml = round(
                    body_mass_kg
                    * _POLICY_V1.pre_workout_hydration_ml_per_kg,
                    1,
                )
        else:
            limitations = ("missing_fresh_body_mass",) + limitations

        during_workout_ml_per_hour = None
        if has_training:
            during_workout_ml_per_hour = (
                _WORKOUT_HYDRATION_ML_PER_HOUR[training_demand]
            )
            limitations += (
                "missing_sweat_rate",
                "missing_environment_data",
            )
        limitations += ("electrolyte_target_unavailable",)

        has_daily_target = daily_ml is not None
        has_workout_target = during_workout_ml_per_hour is not None
        has_duration = nutrition_input.planned_duration_min is not None

        if training_demand is _TrainingDemand.UNKNOWN:
            score = 0.125 if has_daily_target else 0.0
        elif training_demand is _TrainingDemand.REST:
            score = 0.25 if has_daily_target else 0.0
        elif has_daily_target and has_workout_target and has_duration:
            score = 0.25
        elif has_daily_target or has_workout_target:
            score = 0.125
        else:
            score = 0.0

        if score < 0.25:
            limitations += ("missing_hydration_target",)

        return (
            HydrationTarget(
                daily_ml=daily_ml,
                daily_ml_per_kg=daily_ml_per_kg,
                pre_workout_ml=pre_workout_ml,
                during_workout_ml_per_hour=during_workout_ml_per_hour,
                post_workout_ml=None,
            ),
            score,
            limitations,
        )

    @staticmethod
    def _during_carbohydrate_rate(
        duration_min: int,
        training_demand: _TrainingDemand,
    ) -> float:
        if (
            duration_min <= _POLICY_V1.short_workout_max_duration_min
            or training_demand is _TrainingDemand.RECOVERY
        ):
            return _POLICY_V1.short_workout_carbohydrate_g_per_hour
        if (
            training_demand is _TrainingDemand.HIGH
            or duration_min >= _POLICY_V1.long_workout_min_duration_min
        ):
            return _POLICY_V1.high_carbohydrate_g_per_hour
        if training_demand is _TrainingDemand.TEMPO:
            return _POLICY_V1.tempo_carbohydrate_g_per_hour
        return _POLICY_V1.endurance_carbohydrate_g_per_hour

    @staticmethod
    def _fresh_body_mass(nutrition_input: NutritionInput) -> float | None:
        body_mass = nutrition_input.body_mass_kg
        observed_at = nutrition_input.body_mass_observed_at
        if body_mass is None or observed_at is None:
            return None
        if nutrition_input.as_of - observed_at > _POLICY_V1.body_mass_max_age:
            return None
        return body_mass

    @staticmethod
    def _classify_training_demand(
        nutrition_input: NutritionInput,
    ) -> _TrainingDemand:
        workout_type = (nutrition_input.planned_workout_type or "").lower()
        intensity = (nutrition_input.planned_intensity or "").lower()
        duration = nutrition_input.planned_duration_min
        target_tss = nutrition_input.planned_target_tss

        has_training_facts = any(
            value is not None
            for value in (
                nutrition_input.planned_workout_type,
                duration,
                target_tss,
                nutrition_input.planned_intensity,
            )
        )
        if not has_training_facts:
            return _TrainingDemand.UNKNOWN
        if workout_type in {"rest", "off", "rest_day"}:
            return _TrainingDemand.REST
        if (
            workout_type in {"vo2", "vo2max", "vo2_max", "threshold"}
            or intensity in {"high", "very_high"}
            or (
                target_tss is not None
                and target_tss >= _POLICY_V1.high_training_tss
            )
        ):
            return _TrainingDemand.HIGH
        if workout_type == "tempo" or intensity == "moderate":
            return _TrainingDemand.TEMPO
        if (
            workout_type in {"recovery", "easy", "light"}
            or intensity in {"recovery", "easy", "low"}
        ):
            return _TrainingDemand.RECOVERY
        if (
            duration is not None
            and duration <= _POLICY_V1.short_workout_max_duration_min
        ):
            return _TrainingDemand.RECOVERY
        if (
            duration is not None
            and duration >= _POLICY_V1.long_workout_min_duration_min
        ):
            return _TrainingDemand.HIGH
        if workout_type in {"endurance", "base", "long"}:
            return _TrainingDemand.ENDURANCE
        return _TrainingDemand.ENDURANCE

    @classmethod
    def _validate(cls, nutrition_input: NutritionInput) -> None:
        for field_name in (
            "body_mass_kg",
            "resting_energy_kcal",
            "active_energy_kcal",
            "recovery_score",
            "planned_duration_min",
            "planned_target_tss",
        ):
            cls._validate_non_negative_finite(
                field_name,
                getattr(nutrition_input, field_name),
            )

        if nutrition_input.body_mass_kg == 0:
            raise ValueError("body_mass_kg must be positive")

        if (
            nutrition_input.body_mass_observed_at is not None
            and nutrition_input.body_mass_kg is None
        ):
            raise ValueError(
                "body_mass_observed_at requires body_mass_kg"
            )

        if (
            nutrition_input.energy_observed_for_date is not None
            and nutrition_input.resting_energy_kcal is None
            and nutrition_input.active_energy_kcal is None
        ):
            raise ValueError(
                "energy_observed_for_date requires an energy value"
            )

        energy_date = nutrition_input.energy_observed_for_date
        if energy_date is not None:
            if energy_date > nutrition_input.valid_for_date:
                raise ValueError(
                    "energy_observed_for_date cannot be after valid_for_date"
                )
            if energy_date > nutrition_input.as_of.date():
                raise ValueError(
                    "energy_observed_for_date cannot be after as_of"
                )

        if nutrition_input.body_mass_observed_at is not None:
            cls._validate_not_after_as_of(
                "body_mass_observed_at",
                nutrition_input.body_mass_observed_at,
                nutrition_input.as_of,
            )

        if nutrition_input.workout_start is not None:
            cls._validate_compatible_timezones(
                "workout_start",
                nutrition_input.workout_start,
                nutrition_input.as_of,
            )
            if (
                nutrition_input.workout_start.date()
                != nutrition_input.valid_for_date
            ):
                raise ValueError(
                    "workout_start must fall on valid_for_date"
                )

    @staticmethod
    def _validate_non_negative_finite(
        field_name: str,
        value: float | int | None,
    ) -> None:
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be a number")
        if not isfinite(value):
            raise ValueError(f"{field_name} must be finite")
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative")

    @staticmethod
    def _validate_not_after_as_of(
        field_name: str,
        observed_at: datetime,
        as_of: datetime,
    ) -> None:
        NutritionEngine._validate_compatible_timezones(
            field_name,
            observed_at,
            as_of,
        )
        if observed_at > as_of:
            raise ValueError(f"{field_name} cannot be after as_of")

    @staticmethod
    def _validate_compatible_timezones(
        field_name: str,
        observed_at: datetime,
        as_of: datetime,
    ) -> None:
        try:
            _ = observed_at <= as_of
        except TypeError as error:
            raise ValueError(
                f"{field_name} and as_of must use compatible timezones"
            ) from error

    @staticmethod
    def _stable_unique(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))
