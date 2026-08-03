from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone

import pytest

from adaptive import (
    AthleteGoal,
    AthleteGoalType,
    BodyMassTrendQuality,
    BodyMassTrendQualityDataStatus,
    GoalAssessmentDataStatus,
    GoalAssessmentEngine,
)
from application.adaptation import AdaptationDirective, AdaptationStatus
from body_composition import (
    BodyCompositionAssessment,
    BodyCompositionDataStatus,
    BodyCompositionProfile,
    BodyMassTrend,
    BodyMeasurement,
)


VALID_FOR_DATE = date(2026, 8, 10)
AS_OF = datetime(2026, 8, 10, 6)


def _goal(
    *,
    goal_type: AthleteGoalType = AthleteGoalType.MAINTAIN,
    target_body_mass_kg: float | None = None,
    valid_from: date = date(2026, 8, 1),
    valid_until: date | None = None,
    recorded_at: datetime = datetime(2026, 8, 1, 6),
    evidence: tuple[str, ...] = ("goal",),
) -> AthleteGoal:
    return AthleteGoal(
        id="goal-1",
        goal_type=goal_type,
        valid_from=valid_from,
        recorded_at=recorded_at,
        target_body_mass_kg=target_body_mass_kg,
        valid_until=valid_until,
        evidence=evidence,
    )


def _body_composition(
    *,
    current_mass: bool = True,
    trend: bool = True,
    data_status: BodyCompositionDataStatus = BodyCompositionDataStatus.PARTIAL,
    valid_for_date: date = VALID_FOR_DATE,
    as_of: datetime = AS_OF,
    evidence: tuple[str, ...] = ("body",),
) -> BodyCompositionAssessment:
    current = BodyMeasurement(
        value=80.0,
        observed_at=datetime(2026, 8, 10),
    )
    body_mass_trend = None
    if trend:
        body_mass_trend = BodyMassTrend(
            current=current,
            baseline=BodyMeasurement(
                value=81.0,
                observed_at=datetime(2026, 7, 13),
            ),
            period_days=28,
            absolute_change_kg=-1.0,
            percentage_change=-1.234567,
        )
    return BodyCompositionAssessment(
        profile=BodyCompositionProfile(
            body_mass=current if current_mass else None,
        ),
        body_mass_trend=body_mass_trend,
        data_status=data_status,
        confidence=0.5,
        evidence=evidence,
        limitations=(),
        valid_for_date=valid_for_date,
        as_of=as_of,
    )


def _trend_quality(
    *,
    data_status: BodyMassTrendQualityDataStatus = (
        BodyMassTrendQualityDataStatus.COMPLETE
    ),
    source_consistency_known: bool = True,
    valid_for_date: date = VALID_FOR_DATE,
    as_of: datetime = AS_OF,
    evidence: tuple[str, ...] = ("quality",),
    limitations: tuple[str, ...] = (),
) -> BodyMassTrendQuality:
    confidence_by_status = {
        BodyMassTrendQualityDataStatus.COMPLETE: 1.0,
        BodyMassTrendQualityDataStatus.PARTIAL: 0.75,
        BodyMassTrendQualityDataStatus.INSUFFICIENT_DATA: 0.0,
    }
    return BodyMassTrendQuality(
        measurement_count=2,
        period_days=28,
        current_is_fresh=True,
        baseline_window_valid=True,
        source_consistency_known=source_consistency_known,
        data_status=data_status,
        confidence=confidence_by_status[data_status],
        evidence=evidence,
        limitations=limitations,
        valid_for_date=valid_for_date,
        as_of=as_of,
    )


def _adaptation(
    status: AdaptationStatus = AdaptationStatus.MAINTAIN,
    *,
    as_of: datetime = AS_OF,
) -> AdaptationDirective:
    return AdaptationDirective(as_of=as_of, status=status, source_reasons=())


def _analyze(
    *,
    goal: AthleteGoal | None = None,
    body_composition: BodyCompositionAssessment | None = None,
    trend_quality: BodyMassTrendQuality | None = None,
    adaptation: AdaptationDirective | None = None,
    valid_for_date: date = VALID_FOR_DATE,
    as_of: datetime = AS_OF,
):
    return GoalAssessmentEngine().analyze(
        goal=_goal() if goal is None else goal,
        body_composition=body_composition or _body_composition(),
        trend_quality=trend_quality or _trend_quality(),
        adaptation=_adaptation() if adaptation is None else adaptation,
        valid_for_date=valid_for_date,
        as_of=as_of,
    )


def test_missing_goal_returns_stable_insufficient_assessment():
    result = GoalAssessmentEngine().analyze(
        goal=None,
        body_composition=_body_composition(),
        trend_quality=_trend_quality(),
        adaptation=_adaptation(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert result.goal is None
    assert result.data_status is GoalAssessmentDataStatus.INSUFFICIENT_DATA
    assert result.confidence == 0.0
    assert result.limitations == ("missing_active_goal",)


@pytest.mark.parametrize(
    "goal",
    (
        _goal(valid_until=VALID_FOR_DATE - timedelta(days=1)),
        _goal(valid_from=VALID_FOR_DATE + timedelta(days=1)),
        _goal(recorded_at=AS_OF + timedelta(seconds=1)),
    ),
)
def test_inactive_goal_returns_stable_insufficient_assessment(goal):
    result = _analyze(goal=goal)

    assert result.goal is None
    assert result.data_status is GoalAssessmentDataStatus.INSUFFICIENT_DATA
    assert result.confidence == 0.0
    assert result.limitations == ("inactive_goal",)


@pytest.mark.parametrize(
    "goal",
    (
        _goal(valid_from=VALID_FOR_DATE),
        _goal(valid_until=VALID_FOR_DATE),
    ),
)
def test_goal_validity_boundaries_are_inclusive(goal):
    assert _analyze(goal=goal).goal == goal


def test_mixed_goal_and_request_timezones_are_rejected():
    aware_as_of = AS_OF.replace(tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="compatible timezones"):
        _analyze(as_of=aware_as_of)


def test_maintain_goal_needs_no_target_for_complete_assessment():
    result = _analyze(goal=_goal(target_body_mass_kg=None))

    assert result.data_status is GoalAssessmentDataStatus.COMPLETE
    assert result.confidence == 1.0
    assert result.limitations == ()


def test_reduce_body_mass_goal_with_target_can_be_complete():
    result = _analyze(
        goal=_goal(
            goal_type=AthleteGoalType.REDUCE_BODY_MASS,
            target_body_mass_kg=75.0,
        )
    )

    assert result.data_status is GoalAssessmentDataStatus.COMPLETE
    assert result.confidence == 1.0


def test_reduce_body_mass_goal_without_target_is_partial():
    result = _analyze(
        goal=_goal(goal_type=AthleteGoalType.REDUCE_BODY_MASS)
    )

    assert result.data_status is GoalAssessmentDataStatus.PARTIAL
    assert result.confidence == 0.8
    assert result.limitations == ("missing_target_body_mass",)


@pytest.mark.parametrize(
    "body_composition,limitation",
    (
        (_body_composition(current_mass=False), "missing_current_body_mass"),
        (_body_composition(trend=False), "missing_body_mass_trend"),
        (
            _body_composition(
                data_status=BodyCompositionDataStatus.INSUFFICIENT_DATA
            ),
            "insufficient_body_composition",
        ),
    ),
)
def test_incomplete_body_composition_section_is_partial(
    body_composition,
    limitation,
):
    result = _analyze(body_composition=body_composition)

    assert result.data_status is GoalAssessmentDataStatus.PARTIAL
    assert result.confidence == 0.8
    assert limitation in result.limitations


def test_partial_trend_quality_is_partial_and_preserves_source_limitation():
    quality = _trend_quality(
        data_status=BodyMassTrendQualityDataStatus.PARTIAL,
        source_consistency_known=False,
        limitations=("source_consistency_unknown",),
    )

    result = _analyze(trend_quality=quality)

    assert result.data_status is GoalAssessmentDataStatus.PARTIAL
    assert result.confidence == 0.8
    assert result.limitations == (
        "insufficient_trend_quality",
        "source_consistency_unknown",
    )


def test_insufficient_trend_quality_is_a_hard_gate():
    quality = _trend_quality(
        data_status=BodyMassTrendQualityDataStatus.INSUFFICIENT_DATA,
        source_consistency_known=False,
        limitations=("missing_body_mass_trend",),
    )

    result = _analyze(trend_quality=quality)

    assert result.data_status is GoalAssessmentDataStatus.INSUFFICIENT_DATA
    assert result.confidence == 0.0
    assert result.limitations == (
        "insufficient_trend_quality",
        "missing_body_mass_trend",
        "source_consistency_unknown",
    )


def test_missing_safety_context_prevents_complete_status():
    result = GoalAssessmentEngine().analyze(
        goal=_goal(),
        body_composition=_body_composition(),
        trend_quality=_trend_quality(),
        adaptation=None,
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert result.data_status is GoalAssessmentDataStatus.PARTIAL
    assert result.confidence == 0.8
    assert result.limitations == ("safety_context_unavailable",)


@pytest.mark.parametrize(
    "status,limitation",
    (
        (
            AdaptationStatus.REDUCE_LOAD,
            "training_recovery_safety_active",
        ),
        (
            AdaptationStatus.INSUFFICIENT_DATA,
            "safety_context_unavailable",
        ),
    ),
)
def test_non_neutral_safety_directive_prevents_complete_status(
    status,
    limitation,
):
    result = _analyze(adaptation=_adaptation(status))

    assert result.data_status is GoalAssessmentDataStatus.PARTIAL
    assert result.confidence == 0.8
    assert result.limitations == (limitation,)


def test_future_safety_directive_is_rejected():
    with pytest.raises(ValueError, match="cannot be after"):
        _analyze(adaptation=_adaptation(as_of=AS_OF + timedelta(seconds=1)))


@pytest.mark.parametrize(
    "body_composition,trend_quality,error",
    (
        (
            _body_composition(valid_for_date=date(2026, 8, 9)),
            _trend_quality(),
            "body_composition valid_for_date",
        ),
        (
            _body_composition(),
            _trend_quality(valid_for_date=date(2026, 8, 9)),
            "trend_quality valid_for_date",
        ),
        (
            _body_composition(as_of=AS_OF - timedelta(seconds=1)),
            _trend_quality(),
            "body_composition as_of",
        ),
    ),
)
def test_mismatched_assessment_temporality_is_rejected(
    body_composition,
    trend_quality,
    error,
):
    with pytest.raises(ValueError, match=error):
        _analyze(
            body_composition=body_composition,
            trend_quality=trend_quality,
        )


def test_evidence_is_merged_deduplicated_and_sorted_without_parsing():
    result = _analyze(
        goal=_goal(evidence=("z", "a")),
        body_composition=_body_composition(evidence=("b", "a")),
        trend_quality=_trend_quality(evidence=("z", "c")),
    )

    assert result.evidence == ("a", "b", "c", "z")


def test_limitations_are_deterministic_and_deduplicated():
    quality = _trend_quality(
        data_status=BodyMassTrendQualityDataStatus.PARTIAL,
        source_consistency_known=False,
        limitations=(
            "source_consistency_unknown",
            "source_consistency_unknown",
        ),
    )

    first = _analyze(trend_quality=quality, adaptation=_adaptation())
    second = _analyze(trend_quality=quality, adaptation=_adaptation())

    assert first == second
    assert first.limitations == (
        "insufficient_trend_quality",
        "source_consistency_unknown",
    )


def test_output_is_immutable_and_inputs_are_not_mutated():
    goal = _goal()
    body_composition = _body_composition()
    trend_quality = _trend_quality()
    adaptation = _adaptation()
    originals = deepcopy((goal, body_composition, trend_quality, adaptation))

    result = _analyze(
        goal=goal,
        body_composition=body_composition,
        trend_quality=trend_quality,
        adaptation=adaptation,
    )

    assert (goal, body_composition, trend_quality, adaptation) == originals
    with pytest.raises(FrozenInstanceError):
        result.confidence = 0.0


def test_public_engine_is_stateless_and_repeatable():
    engine = GoalAssessmentEngine()

    first = engine.analyze(
        goal=_goal(),
        body_composition=_body_composition(),
        trend_quality=_trend_quality(),
        adaptation=_adaptation(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )
    second = engine.analyze(
        goal=_goal(),
        body_composition=_body_composition(),
        trend_quality=_trend_quality(),
        adaptation=_adaptation(),
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert first == second
    assert vars(engine) == {}


def test_public_package_exports_goal_assessment_engine():
    assert GoalAssessmentEngine.__module__ == "adaptive.assessment"


def test_model_accepts_absent_goal_for_insufficient_assessment():
    result = GoalAssessmentEngine().analyze(
        goal=None,
        body_composition=_body_composition(),
        trend_quality=_trend_quality(),
        adaptation=None,
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )

    assert replace(result, limitations=result.limitations) == result
