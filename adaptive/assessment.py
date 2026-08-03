from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from adaptive.goals import ActiveGoalSelector
from adaptive.models import (
    AthleteGoal,
    AthleteGoalType,
    BodyMassTrendQuality,
    BodyMassTrendQualityDataStatus,
    GoalAssessment,
    GoalAssessmentDataStatus,
)
from body_composition.models import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
)

if TYPE_CHECKING:
    from application.adaptation import AdaptationDirective


class GoalAssessmentEngine:
    """Assess completeness of context for later goal recommendations.

    Confidence is a completeness score composed of five equal sections:
    active goal, complete goal configuration, current mass with a trend,
    complete trend quality, and available non-restrictive safety context.
    It is not a probability, accuracy, sensor-quality, or clinical score.
    Insufficient trend quality is a hard gate and yields an insufficient
    assessment with zero confidence.
    """

    def analyze(
        self,
        *,
        goal: AthleteGoal | None,
        body_composition: BodyCompositionAssessment,
        trend_quality: BodyMassTrendQuality,
        adaptation: AdaptationDirective | None,
        valid_for_date: date,
        as_of: datetime,
    ) -> GoalAssessment:
        self._validate_request_date(valid_for_date, as_of)
        evidence = self._merge_evidence(goal, body_composition, trend_quality)

        if goal is None:
            return self._insufficient(
                goal=None,
                valid_for_date=valid_for_date,
                as_of=as_of,
                evidence=evidence,
                limitation="missing_active_goal",
            )

        active_goal = ActiveGoalSelector().select(
            (goal,),
            valid_for_date=valid_for_date,
            as_of=as_of,
        )
        if active_goal is None:
            return self._insufficient(
                goal=None,
                valid_for_date=valid_for_date,
                as_of=as_of,
                evidence=evidence,
                limitation="inactive_goal",
            )

        self._validate_assessment_inputs(
            body_composition,
            trend_quality,
            valid_for_date,
            as_of,
        )
        safety_complete, safety_limitation = self._evaluate_safety(
            adaptation,
            as_of,
        )

        limitations: list[str] = []
        goal_configuration_complete = True
        if (
            active_goal.goal_type is AthleteGoalType.REDUCE_BODY_MASS
            and active_goal.target_body_mass_kg is None
        ):
            goal_configuration_complete = False
            self._append_unique(limitations, "missing_target_body_mass")

        current_mass_available = body_composition.profile.body_mass is not None
        trend_available = body_composition.body_mass_trend is not None
        body_composition_sufficient = (
            body_composition.data_status
            is not BodyCompositionDataStatus.INSUFFICIENT_DATA
        )
        if not current_mass_available:
            self._append_unique(limitations, "missing_current_body_mass")
        if not trend_available:
            self._append_unique(limitations, "missing_body_mass_trend")
        if not body_composition_sufficient:
            self._append_unique(limitations, "insufficient_body_composition")
        body_section_complete = (
            current_mass_available
            and trend_available
            and body_composition_sufficient
        )

        trend_section_complete = (
            trend_quality.data_status
            is BodyMassTrendQualityDataStatus.COMPLETE
        )
        if not trend_section_complete:
            self._append_unique(limitations, "insufficient_trend_quality")
        for limitation in trend_quality.limitations:
            self._append_unique(limitations, limitation)
        if not trend_quality.source_consistency_known:
            self._append_unique(limitations, "source_consistency_unknown")

        if safety_limitation is not None:
            self._append_unique(limitations, safety_limitation)

        if (
            trend_quality.data_status
            is BodyMassTrendQualityDataStatus.INSUFFICIENT_DATA
        ):
            return GoalAssessment(
                goal=active_goal,
                data_status=GoalAssessmentDataStatus.INSUFFICIENT_DATA,
                confidence=0.0,
                valid_for_date=valid_for_date,
                as_of=as_of,
                evidence=evidence,
                limitations=tuple(limitations),
            )

        confidence = sum(
            0.2
            for section_complete in (
                True,
                goal_configuration_complete,
                body_section_complete,
                trend_section_complete,
                safety_complete,
            )
            if section_complete
        )
        status = (
            GoalAssessmentDataStatus.COMPLETE
            if confidence == 1.0
            else GoalAssessmentDataStatus.PARTIAL
        )
        return GoalAssessment(
            goal=active_goal,
            data_status=status,
            confidence=confidence,
            valid_for_date=valid_for_date,
            as_of=as_of,
            evidence=evidence,
            limitations=tuple(limitations),
        )

    @staticmethod
    def _validate_request_date(valid_for_date: date, as_of: datetime) -> None:
        if isinstance(valid_for_date, datetime) or not isinstance(
            valid_for_date,
            date,
        ):
            raise TypeError("valid_for_date must be a date")
        if not isinstance(as_of, datetime):
            raise TypeError("as_of must be a datetime")
        if valid_for_date > as_of.date():
            raise ValueError("valid_for_date cannot be after as_of")

    @classmethod
    def _validate_assessment_inputs(
        cls,
        body_composition: BodyCompositionAssessment,
        trend_quality: BodyMassTrendQuality,
        valid_for_date: date,
        as_of: datetime,
    ) -> None:
        if not isinstance(body_composition, BodyCompositionAssessment):
            raise TypeError(
                "body_composition must be a BodyCompositionAssessment"
            )
        if not isinstance(trend_quality, BodyMassTrendQuality):
            raise TypeError("trend_quality must be a BodyMassTrendQuality")
        if not isinstance(
            body_composition.data_status,
            BodyCompositionDataStatus,
        ):
            raise TypeError(
                "body_composition data_status must be a "
                "BodyCompositionDataStatus"
            )
        if not isinstance(
            trend_quality.data_status,
            BodyMassTrendQualityDataStatus,
        ):
            raise TypeError(
                "trend_quality data_status must be a "
                "BodyMassTrendQualityDataStatus"
            )
        if not isinstance(trend_quality.source_consistency_known, bool):
            raise TypeError("source_consistency_known must be a bool")
        if body_composition.valid_for_date != valid_for_date:
            raise ValueError("body_composition valid_for_date must match")
        if trend_quality.valid_for_date != valid_for_date:
            raise ValueError("trend_quality valid_for_date must match")
        cls._validate_matching_datetime(
            "body_composition as_of",
            body_composition.as_of,
            as_of,
        )
        cls._validate_matching_datetime(
            "trend_quality as_of",
            trend_quality.as_of,
            as_of,
        )

    @classmethod
    def _evaluate_safety(
        cls,
        adaptation: AdaptationDirective | None,
        as_of: datetime,
    ) -> tuple[bool, str | None]:
        if adaptation is None:
            return False, "safety_context_unavailable"

        from application.adaptation import AdaptationDirective, AdaptationStatus

        if not isinstance(adaptation, AdaptationDirective):
            raise TypeError("adaptation must be an AdaptationDirective or None")
        cls._validate_not_after_datetime(
            "adaptation as_of",
            adaptation.as_of,
            as_of,
        )
        if adaptation.status is AdaptationStatus.MAINTAIN:
            return True, None
        if adaptation.status is AdaptationStatus.REDUCE_LOAD:
            return False, "training_recovery_safety_active"
        if adaptation.status is AdaptationStatus.INSUFFICIENT_DATA:
            return False, "safety_context_unavailable"
        raise ValueError("unsupported adaptation status")

    @staticmethod
    def _validate_matching_datetime(
        field_name: str,
        value: datetime,
        expected: datetime,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(f"{field_name} must be a datetime")
        try:
            matches = value == expected
            value <= expected
        except TypeError as error:
            raise ValueError(
                f"{field_name} and request as_of must use compatible timezones"
            ) from error
        if not matches:
            raise ValueError(f"{field_name} must match request as_of")

    @staticmethod
    def _validate_not_after_datetime(
        field_name: str,
        value: datetime,
        maximum: datetime,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(f"{field_name} must be a datetime")
        try:
            is_after = value > maximum
        except TypeError as error:
            raise ValueError(
                f"{field_name} and request as_of must use compatible timezones"
            ) from error
        if is_after:
            raise ValueError(f"{field_name} cannot be after request as_of")

    @staticmethod
    def _merge_evidence(
        goal: AthleteGoal | None,
        body_composition: BodyCompositionAssessment,
        trend_quality: BodyMassTrendQuality,
    ) -> tuple[str, ...]:
        goal_evidence = goal.evidence if isinstance(goal, AthleteGoal) else ()
        body_evidence = (
            body_composition.evidence
            if isinstance(body_composition, BodyCompositionAssessment)
            else ()
        )
        trend_evidence = (
            trend_quality.evidence
            if isinstance(trend_quality, BodyMassTrendQuality)
            else ()
        )
        return tuple(sorted(set(goal_evidence + body_evidence + trend_evidence)))

    @staticmethod
    def _append_unique(values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)

    @staticmethod
    def _insufficient(
        *,
        goal: AthleteGoal | None,
        valid_for_date: date,
        as_of: datetime,
        evidence: tuple[str, ...],
        limitation: str,
    ) -> GoalAssessment:
        return GoalAssessment(
            goal=goal,
            data_status=GoalAssessmentDataStatus.INSUFFICIENT_DATA,
            confidence=0.0,
            valid_for_date=valid_for_date,
            as_of=as_of,
            evidence=evidence,
            limitations=(limitation,),
        )
