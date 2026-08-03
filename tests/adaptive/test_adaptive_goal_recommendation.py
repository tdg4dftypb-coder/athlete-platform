from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from adaptive import (
    AdaptiveGoalRecommendationRule,
    AthleteGoal,
    AthleteGoalType,
    GoalAssessment,
    GoalAssessmentDataStatus,
)
from recommendation import (
    RecommendationContext,
    RecommendationPriority,
    RecommendationRule,
    RecommendationType,
)


VALID_FOR_DATE = date(2026, 8, 10)
AS_OF = datetime(2026, 8, 10, 6)


def _goal() -> AthleteGoal:
    return AthleteGoal(
        id="goal-1",
        goal_type=AthleteGoalType.MAINTAIN,
        valid_from=VALID_FOR_DATE,
        recorded_at=AS_OF,
        evidence=("goal",),
    )


def _assessment(
    *,
    goal: AthleteGoal | None = None,
    data_status: GoalAssessmentDataStatus = GoalAssessmentDataStatus.COMPLETE,
    confidence: float = 1.0,
    evidence: tuple[str, ...] = ("body", "goal", "quality"),
    limitations: tuple[str, ...] = (),
) -> GoalAssessment:
    return GoalAssessment(
        goal=_goal() if goal is None else goal,
        data_status=data_status,
        confidence=confidence,
        evidence=evidence,
        limitations=limitations,
        valid_for_date=VALID_FOR_DATE,
        as_of=AS_OF,
    )


def _context(
    assessment: GoalAssessment | None = None,
) -> RecommendationContext:
    return RecommendationContext(
        decision=SimpleNamespace(decision_reasons=(), confidence=0.0),
        insights=(),
        observations=(),
        goal_assessment=assessment,
    )


def test_missing_goal_assessment_returns_no_recommendation():
    assert AdaptiveGoalRecommendationRule().evaluate(_context()) == ()


@pytest.mark.parametrize(
    "status",
    (
        GoalAssessmentDataStatus.INSUFFICIENT_DATA,
        GoalAssessmentDataStatus.PARTIAL,
    ),
)
def test_incomplete_goal_assessment_returns_no_recommendation(status):
    assert AdaptiveGoalRecommendationRule().evaluate(
        _context(_assessment(data_status=status, confidence=0.8))
    ) == ()


def test_complete_safe_assessment_returns_neutral_review_recommendation():
    assessment = _assessment()

    recommendation = AdaptiveGoalRecommendationRule().evaluate(
        _context(assessment)
    )[0]

    assert (
        recommendation.type
        is RecommendationType.REVIEW_BODY_COMPOSITION_TREND
    )
    assert recommendation.priority is RecommendationPriority.MEDIUM
    assert recommendation.confidence == assessment.confidence
    assert recommendation.evidence is assessment.evidence
    assert recommendation.source_rules == ("AdaptiveGoalRecommendationRule",)
    assert recommendation.as_of is assessment.as_of


def test_complete_assessment_with_limitation_does_not_activate():
    assessment = _assessment(limitations=("source_consistency_unknown",))

    assert AdaptiveGoalRecommendationRule().evaluate(_context(assessment)) == ()


def test_confidence_below_one_does_not_activate():
    assessment = _assessment(confidence=0.8)

    assert AdaptiveGoalRecommendationRule().evaluate(_context(assessment)) == ()


def test_complete_assessment_without_goal_does_not_activate():
    assessment = replace(_assessment(), goal=None)

    assert AdaptiveGoalRecommendationRule().evaluate(_context(assessment)) == ()


def test_output_is_immutable_deterministic_and_does_not_mutate_inputs():
    assessment = _assessment()
    context = _context(assessment)
    original = deepcopy((assessment, context))
    rule = AdaptiveGoalRecommendationRule()

    first = rule.evaluate(context)
    second = rule.evaluate(context)

    assert first == second
    assert (assessment, context) == original
    with pytest.raises(FrozenInstanceError):
        context.goal_assessment = None
    with pytest.raises(FrozenInstanceError):
        first[0].confidence = 0.5


def test_rule_implements_the_existing_global_recommendation_contract():
    assert isinstance(AdaptiveGoalRecommendationRule(), RecommendationRule)


def test_rule_requires_only_the_prepared_goal_assessment():
    assessment = _assessment()
    context = _context(assessment)

    assert not hasattr(context, "body_composition")
    assert not hasattr(context, "body_mass_trend_quality")
    assert len(AdaptiveGoalRecommendationRule().evaluate(context)) == 1
