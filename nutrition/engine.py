from __future__ import annotations

from datetime import datetime
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


class NutritionEngine:
    """Build the energy portion of an aggregate nutrition assessment."""

    def analyze(self, nutrition_input: NutritionInput) -> NutritionAssessment:
        self._validate(nutrition_input)

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
            data_status = NutritionDataStatus.PARTIAL
            confidence = 0.25
        elif has_resting_energy or has_active_energy:
            observed_expenditure = None
            data_status = NutritionDataStatus.PARTIAL
            confidence = 0.125
        else:
            observed_expenditure = None
            data_status = NutritionDataStatus.INSUFFICIENT_DATA
            confidence = 0.0

        energy_limitations = tuple(
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
        )
        limitations = energy_limitations + (
            "missing_estimated_daily_requirement",
            "missing_macro_targets",
            "missing_fueling_plan",
            "missing_hydration_target",
            "missing_energy_intake",
        )

        return NutritionAssessment(
            energy_requirement=EnergyRequirement(
                estimated_daily_requirement_kcal=None,
                observed_daily_expenditure_kcal=observed_expenditure,
                resting_energy_kcal=nutrition_input.resting_energy_kcal,
                active_energy_kcal=nutrition_input.active_energy_kcal,
            ),
            macro_targets=MacroTargets(),
            fueling_plan=FuelingPlan(),
            hydration_target=HydrationTarget(),
            data_status=data_status,
            confidence=confidence,
            evidence=tuple(sorted(set(nutrition_input.evidence))),
            limitations=limitations,
            valid_for_date=nutrition_input.valid_for_date,
            as_of=nutrition_input.as_of,
        )

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
