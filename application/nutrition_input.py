from __future__ import annotations

from datetime import date, datetime, time

from core.models import HealthDaily
from decision.models import DecisionResult
from nutrition import NutritionInput


class NutritionInputBuilder:
    """Adapt canonical application facts to a normalized NutritionInput."""

    def build(
        self,
        decision: DecisionResult,
        *,
        valid_for_date: date,
        as_of: datetime,
        health_history: tuple[HealthDaily, ...] = (),
        recovery_score: float | None = None,
        workout_start: datetime | None = None,
        evidence: tuple[str, ...] = (),
    ) -> NutritionInput:
        health_daily = self._health_daily_for(
            health_history,
            valid_for_date,
        )
        body_mass_daily = self._latest_body_mass(
            health_history,
            valid_for_date,
        )

        resting_energy = (
            health_daily.resting_energy if health_daily is not None else None
        )
        active_energy = (
            health_daily.active_energy if health_daily is not None else None
        )
        has_energy = resting_energy is not None or active_energy is not None

        source_evidence = list(evidence)
        if health_daily is not None:
            source_evidence.append(
                f"health_daily:{health_daily.date.isoformat()}"
            )
        if body_mass_daily is not None:
            source_evidence.append(
                f"body_mass:{body_mass_daily.date.isoformat()}"
            )
        source_evidence.append(
            f"decision:{self._enum_value(decision.recommendation)}"
        )

        return NutritionInput(
            valid_for_date=valid_for_date,
            as_of=as_of,
            body_mass_kg=(
                body_mass_daily.weight
                if body_mass_daily is not None
                and body_mass_daily.weight is not None
                else None
            ),
            body_mass_observed_at=(
                self._at_start_of_day(body_mass_daily.date, as_of)
                if body_mass_daily is not None
                else None
            ),
            resting_energy_kcal=(
                resting_energy if resting_energy is not None else None
            ),
            active_energy_kcal=(
                active_energy if active_energy is not None else None
            ),
            energy_observed_for_date=(
                health_daily.date
                if health_daily is not None and has_energy
                else None
            ),
            recovery_score=recovery_score,
            planned_sport=self._enum_value(decision.sport),
            planned_workout_type=self._enum_value(decision.recommendation),
            planned_duration_min=decision.duration,
            planned_target_tss=decision.target_tss,
            planned_intensity=decision.intensity,
            workout_start=workout_start,
            evidence=tuple(sorted(set(source_evidence))),
        )

    @staticmethod
    def _health_daily_for(
        health_history: tuple[HealthDaily, ...],
        valid_for_date: date,
    ) -> HealthDaily | None:
        matching = tuple(
            item for item in health_history if item.date == valid_for_date
        )
        return matching[-1] if matching else None

    @staticmethod
    def _latest_body_mass(
        health_history: tuple[HealthDaily, ...],
        valid_for_date: date,
    ) -> HealthDaily | None:
        candidates = tuple(
            item
            for item in health_history
            if item.date <= valid_for_date and item.weight is not None
        )
        return max(candidates, key=lambda item: item.date, default=None)

    @staticmethod
    def _at_start_of_day(day: date, as_of: datetime) -> datetime:
        return datetime.combine(day, time.min, tzinfo=as_of.tzinfo)

    @staticmethod
    def _enum_value(value: object) -> str:
        return str(getattr(value, "value", value))
