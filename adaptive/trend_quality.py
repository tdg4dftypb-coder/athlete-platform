from datetime import date, datetime, timedelta

from adaptive.models import (
    BodyMassTrendQuality,
    BodyMassTrendQualityDataStatus,
    BodyMassTrendQualityInput,
)
from body_composition.models import BodyCompositionAssessment


_CURRENT_BODY_MASS_MAX_AGE_V1 = timedelta(days=30)
_BASELINE_WINDOW_MIN_DAYS_V1 = 21
_BASELINE_WINDOW_MAX_DAYS_V1 = 35


class BodyMassTrendQualityEvaluator:
    """Evaluate completeness of body-mass trend facts without interpreting it."""

    def evaluate(
        self,
        quality_input: BodyMassTrendQualityInput,
    ) -> BodyMassTrendQuality:
        self._validate(quality_input)

        assessment = quality_input.assessment
        trend = assessment.body_mass_trend
        measurement_count = quality_input.measurement_count
        trend_exists = trend is not None
        count_is_sufficient = (
            measurement_count is not None and measurement_count >= 2
        )
        current = (
            trend.current
            if trend is not None
            else assessment.profile.body_mass
        )
        current_is_fresh = (
            current is not None
            and timedelta(0)
            <= quality_input.valid_for_date - current.observed_at.date()
            <= _CURRENT_BODY_MASS_MAX_AGE_V1
        )
        baseline_window_valid = (
            trend is not None
            and _BASELINE_WINDOW_MIN_DAYS_V1
            <= trend.period_days
            <= _BASELINE_WINDOW_MAX_DAYS_V1
            and (
                trend.current.observed_at.date()
                - trend.baseline.observed_at.date()
            ).days
            == trend.period_days
        )
        temporal_quality_complete = current_is_fresh and baseline_window_valid

        confidence = sum(
            0.25
            for section_complete in (
                trend_exists,
                count_is_sufficient,
                temporal_quality_complete,
                quality_input.source_consistency_known,
            )
            if section_complete
        )
        if confidence == 1.0:
            data_status = BodyMassTrendQualityDataStatus.COMPLETE
        elif confidence > 0.0:
            data_status = BodyMassTrendQualityDataStatus.PARTIAL
        else:
            data_status = BodyMassTrendQualityDataStatus.INSUFFICIENT_DATA

        limitations = []
        if trend is None:
            limitations.append("missing_body_mass_trend")
        if measurement_count is None:
            limitations.append("unknown_measurement_count")
        elif measurement_count < 2:
            limitations.append("insufficient_measurement_count")
        if trend is not None and not baseline_window_valid:
            limitations.append("invalid_trend_period")
        if current is not None and not current_is_fresh:
            limitations.append("stale_current_body_mass")
        if not quality_input.source_consistency_known:
            limitations.append("source_consistency_unknown")

        evidence = tuple(
            sorted(
                set(assessment.evidence).union(quality_input.evidence)
            )
        )

        return BodyMassTrendQuality(
            measurement_count=measurement_count,
            period_days=trend.period_days if trend is not None else None,
            current_is_fresh=current_is_fresh,
            baseline_window_valid=baseline_window_valid,
            source_consistency_known=quality_input.source_consistency_known,
            data_status=data_status,
            confidence=confidence,
            evidence=evidence,
            limitations=tuple(limitations),
            valid_for_date=quality_input.valid_for_date,
            as_of=quality_input.as_of,
        )

    @classmethod
    def _validate(cls, quality_input: BodyMassTrendQualityInput) -> None:
        if not isinstance(quality_input, BodyMassTrendQualityInput):
            raise TypeError("quality_input must be a BodyMassTrendQualityInput")
        if not isinstance(quality_input.assessment, BodyCompositionAssessment):
            raise TypeError("assessment must be a BodyCompositionAssessment")
        if isinstance(quality_input.valid_for_date, datetime) or not isinstance(
            quality_input.valid_for_date,
            date,
        ):
            raise TypeError("valid_for_date must be a date")
        if not isinstance(quality_input.as_of, datetime):
            raise TypeError("as_of must be a datetime")
        if quality_input.valid_for_date > quality_input.as_of.date():
            raise ValueError("valid_for_date cannot be after as_of")
        if quality_input.valid_for_date != quality_input.assessment.valid_for_date:
            raise ValueError("valid_for_date must match assessment")
        cls._validate_same_datetime(
            "as_of",
            quality_input.as_of,
            quality_input.assessment.as_of,
        )
        if quality_input.measurement_count is not None:
            if isinstance(quality_input.measurement_count, bool) or not isinstance(
                quality_input.measurement_count,
                int,
            ):
                raise TypeError("measurement_count must be an integer or None")
            if quality_input.measurement_count < 0:
                raise ValueError("measurement_count cannot be negative")
        if not isinstance(quality_input.source_consistency_known, bool):
            raise TypeError("source_consistency_known must be a bool")

        assessment = quality_input.assessment
        timestamps = tuple(
            timestamp
            for timestamp in (
                (
                    assessment.profile.body_mass.observed_at
                    if assessment.profile.body_mass is not None
                    else None
                ),
                (
                    assessment.body_mass_trend.current.observed_at
                    if assessment.body_mass_trend is not None
                    else None
                ),
                (
                    assessment.body_mass_trend.baseline.observed_at
                    if assessment.body_mass_trend is not None
                    else None
                ),
            )
            if timestamp is not None
        )
        for timestamp in timestamps:
            cls._validate_not_after_as_of(timestamp, quality_input.as_of)

    @staticmethod
    def _validate_same_datetime(
        field_name: str,
        value: datetime,
        expected: datetime,
    ) -> None:
        try:
            matches = value == expected
            value <= expected
        except TypeError as error:
            raise ValueError(
                f"{field_name} values must use compatible timezones"
            ) from error
        if not matches:
            raise ValueError(f"{field_name} must match assessment")

    @staticmethod
    def _validate_not_after_as_of(
        observed_at: datetime,
        as_of: datetime,
    ) -> None:
        try:
            is_after = observed_at > as_of
        except TypeError as error:
            raise ValueError(
                "body mass timestamps and as_of must use compatible timezones"
            ) from error
        if is_after:
            raise ValueError("body mass timestamp cannot be after as_of")
