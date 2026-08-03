from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from math import isfinite

from body_composition.models import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionInput,
    BodyCompositionObservation,
    BodyCompositionProfile,
    BodyMassTrend,
    BodyMeasurement,
)


@dataclass(frozen=True)
class _MetricPolicy:
    input_field: str
    missing_limitation: str
    stale_limitation: str
    must_be_positive: bool = True
    is_percentage: bool = False


_FRESHNESS_MAX_AGE_V1 = timedelta(days=30)
_BODY_MASS_TREND_TARGET_DAYS_V1 = 28
_BODY_MASS_TREND_MIN_DAYS_V1 = 21
_BODY_MASS_TREND_MAX_DAYS_V1 = 35

_METRIC_POLICIES_V1 = (
    _MetricPolicy(
        "body_mass_kg",
        "missing_body_mass",
        "stale_body_mass",
    ),
    _MetricPolicy(
        "body_fat_percent",
        "missing_body_fat_percentage",
        "stale_body_fat_percentage",
        must_be_positive=False,
        is_percentage=True,
    ),
    _MetricPolicy(
        "muscle_mass_kg",
        "missing_muscle_mass",
        "stale_muscle_mass",
    ),
    _MetricPolicy(
        "body_water_percent",
        "missing_body_water_percentage",
        "stale_body_water_percentage",
        must_be_positive=False,
        is_percentage=True,
    ),
    _MetricPolicy(
        "visceral_fat_rating",
        "missing_visceral_fat",
        "stale_visceral_fat",
    ),
    _MetricPolicy(
        "basal_metabolic_rate_kcal",
        "missing_basal_metabolic_rate",
        "stale_basal_metabolic_rate",
    ),
    _MetricPolicy(
        "waist_circumference_cm",
        "missing_waist_circumference",
        "stale_waist_circumference",
    ),
)


class BodyCompositionEngine:
    """Build a deterministic current Body Composition assessment.

    Freshness Policy v1 treats measurements up to and including 30 days old
    as current. The threshold is an explicit MVP policy, not a physiological
    or clinical constant. Body Mass Trend Policy v1 selects a baseline 21 to
    35 days before current, preferring 28 days and then the older tied point.
    """

    def analyze(
        self,
        body_composition_input: BodyCompositionInput,
    ) -> BodyCompositionAssessment:
        self._validate(body_composition_input)

        selected: dict[str, BodyMeasurement | None] = {}
        limitations: list[str] = []
        for policy in _METRIC_POLICIES_V1:
            measurement, limitation = self._select_measurement(
                body_composition_input,
                policy,
            )
            selected[policy.input_field] = measurement
            if limitation is not None:
                limitations.append(limitation)

        profile = BodyCompositionProfile(
            body_mass=selected["body_mass_kg"],
            body_fat=selected["body_fat_percent"],
            muscle_mass=selected["muscle_mass_kg"],
            body_water=selected["body_water_percent"],
            visceral_fat=selected["visceral_fat_rating"],
            basal_metabolic_rate=selected["basal_metabolic_rate_kcal"],
            waist_circumference=selected["waist_circumference_cm"],
        )
        body_mass_trend = self._build_body_mass_trend(
            body_composition_input,
            profile.body_mass,
        )
        if body_mass_trend is None:
            limitations.append("insufficient_body_mass_history")

        confidence = sum(
            0.25
            for field_name in (
                "body_mass_kg",
                "body_fat_percent",
                "muscle_mass_kg",
            )
            if selected[field_name] is not None
        )
        if body_mass_trend is not None:
            confidence += 0.25

        if confidence == 1.0:
            data_status = BodyCompositionDataStatus.COMPLETE
        elif confidence > 0.0:
            data_status = BodyCompositionDataStatus.PARTIAL
        else:
            data_status = BodyCompositionDataStatus.INSUFFICIENT_DATA

        evidence = tuple(
            sorted(
                set(body_composition_input.evidence).union(
                    evidence_item
                    for observation in body_composition_input.observations
                    for evidence_item in observation.evidence
                )
            )
        )

        return BodyCompositionAssessment(
            profile=profile,
            body_mass_trend=body_mass_trend,
            data_status=data_status,
            confidence=confidence,
            evidence=evidence,
            limitations=tuple(limitations),
            valid_for_date=body_composition_input.valid_for_date,
            as_of=body_composition_input.as_of,
        )

    @classmethod
    def _validate(
        cls,
        body_composition_input: BodyCompositionInput,
    ) -> None:
        if (
            body_composition_input.valid_for_date
            > body_composition_input.as_of.date()
        ):
            raise ValueError("valid_for_date cannot be after as_of")

        for observation in body_composition_input.observations:
            if observation.observed_for_date > body_composition_input.valid_for_date:
                raise ValueError(
                    "observation date cannot be after valid_for_date"
                )

            observed_at = cls._at_start_of_day(
                observation.observed_for_date,
                body_composition_input.as_of,
            )
            cls._validate_not_after_as_of(
                "observation",
                observed_at,
                body_composition_input.as_of,
            )

            present_metrics = 0
            for policy in _METRIC_POLICIES_V1:
                value = getattr(observation, policy.input_field)
                if value is None:
                    continue
                present_metrics += 1
                cls._validate_metric(policy, value)

            if present_metrics == 0:
                raise ValueError("observation must contain at least one metric")

        cls._validate_duplicate_conflicts(body_composition_input.observations)

    @staticmethod
    def _validate_metric(
        policy: _MetricPolicy,
        value: object,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{policy.input_field} must be a number")
        if not isfinite(value):
            raise ValueError(f"{policy.input_field} must be finite")
        if policy.is_percentage and not 0.0 <= value <= 100.0:
            raise ValueError(f"{policy.input_field} must be between 0 and 100")
        if policy.must_be_positive and value <= 0.0:
            raise ValueError(f"{policy.input_field} must be positive")

    @staticmethod
    def _validate_duplicate_conflicts(
        observations: tuple[BodyCompositionObservation, ...],
    ) -> None:
        for policy in _METRIC_POLICIES_V1:
            values_by_date: dict[date, float] = {}
            for observation in observations:
                value = getattr(observation, policy.input_field)
                if value is None:
                    continue
                existing = values_by_date.get(observation.observed_for_date)
                if existing is not None and existing != value:
                    raise ValueError(
                        f"conflicting {policy.input_field} values for "
                        f"{observation.observed_for_date.isoformat()}"
                    )
                values_by_date[observation.observed_for_date] = float(value)

    @classmethod
    def _select_measurement(
        cls,
        body_composition_input: BodyCompositionInput,
        policy: _MetricPolicy,
    ) -> tuple[BodyMeasurement | None, str | None]:
        candidates = cls._normalized_metric_history(
            body_composition_input.observations,
            policy,
        )
        if not candidates:
            return None, policy.missing_limitation

        observed_for_date, value = max(candidates, key=lambda item: item[0])
        age = body_composition_input.valid_for_date - observed_for_date
        if age > _FRESHNESS_MAX_AGE_V1:
            return None, policy.stale_limitation

        return (
            BodyMeasurement(
                value=float(value),
                observed_at=cls._at_start_of_day(
                    observed_for_date,
                    body_composition_input.as_of,
                ),
            ),
            None,
        )

    @classmethod
    def _build_body_mass_trend(
        cls,
        body_composition_input: BodyCompositionInput,
        current: BodyMeasurement | None,
    ) -> BodyMassTrend | None:
        if current is None:
            return None

        body_mass_policy = _METRIC_POLICIES_V1[0]
        history = cls._normalized_metric_history(
            body_composition_input.observations,
            body_mass_policy,
        )
        current_date = current.observed_at.date()
        baseline_candidates = tuple(
            (observed_for_date, value, (current_date - observed_for_date).days)
            for observed_for_date, value in history
            if _BODY_MASS_TREND_MIN_DAYS_V1
            <= (current_date - observed_for_date).days
            <= _BODY_MASS_TREND_MAX_DAYS_V1
        )
        if not baseline_candidates:
            return None

        baseline_date, baseline_value, period_days = min(
            baseline_candidates,
            key=lambda candidate: (
                abs(candidate[2] - _BODY_MASS_TREND_TARGET_DAYS_V1),
                candidate[0],
            ),
        )
        baseline = BodyMeasurement(
            value=baseline_value,
            observed_at=cls._at_start_of_day(
                baseline_date,
                body_composition_input.as_of,
            ),
        )
        absolute_change_kg = current.value - baseline.value

        return BodyMassTrend(
            current=current,
            baseline=baseline,
            period_days=period_days,
            absolute_change_kg=absolute_change_kg,
            percentage_change=absolute_change_kg / baseline.value * 100.0,
        )

    @staticmethod
    def _normalized_metric_history(
        observations: tuple[BodyCompositionObservation, ...],
        policy: _MetricPolicy,
    ) -> tuple[tuple[date, float], ...]:
        values_by_date = {
            observation.observed_for_date: float(
                getattr(observation, policy.input_field)
            )
            for observation in observations
            if getattr(observation, policy.input_field) is not None
        }
        return tuple(sorted(values_by_date.items()))

    @staticmethod
    def _at_start_of_day(day: date, as_of: datetime) -> datetime:
        return datetime.combine(day, time.min, tzinfo=as_of.tzinfo)

    @staticmethod
    def _validate_not_after_as_of(
        field_name: str,
        observed_at: datetime,
        as_of: datetime,
    ) -> None:
        try:
            is_after = observed_at > as_of
        except TypeError as error:
            raise ValueError(
                f"{field_name} and as_of must use compatible timezones"
            ) from error
        if is_after:
            raise ValueError(f"{field_name} cannot be after as_of")
