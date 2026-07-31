from datetime import datetime
from types import SimpleNamespace

import pytest

from recommendation import (
    Recommendation,
    RecommendationBuilder,
    RecommendationContext,
    RecommendationEngine,
    RecommendationPriority,
    RecommendationResult,
    RecommendationType,
)


AS_OF = datetime(2026, 7, 31, 8)


def _recommendation(
    recommendation_type: RecommendationType,
    *,
    source_rule: str = "FakeRule",
) -> Recommendation:
    return Recommendation(
        id=f"candidate:{recommendation_type.value}:{source_rule}",
        type=recommendation_type,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.8,
        evidence=(f"evidence:{source_rule}",),
        source_rules=(source_rule,),
        as_of=AS_OF,
    )


def _context() -> RecommendationContext:
    return RecommendationContext(
        decision=SimpleNamespace(),
        insights=(),
        observations=(),
    )


class FakeRule:
    def __init__(self, recommendations: tuple[Recommendation, ...]) -> None:
        self.recommendations = recommendations
        self.contexts: list[RecommendationContext] = []

    def evaluate(
        self,
        context: RecommendationContext,
    ) -> tuple[Recommendation, ...]:
        self.contexts.append(context)
        return self.recommendations


class SpyBuilder:
    def __init__(self, result: RecommendationResult) -> None:
        self.result = result
        self.calls: list[tuple[Recommendation, ...]] = []

    def build(
        self,
        candidates: tuple[Recommendation, ...],
    ) -> RecommendationResult:
        self.calls.append(candidates)
        return self.result


def test_engine_without_rules_passes_an_empty_tuple_to_builder():
    expected = RecommendationResult(recommendations=(), as_of=None)
    builder = SpyBuilder(expected)

    result = RecommendationEngine((), builder).evaluate(_context())

    assert builder.calls == [()]
    assert result is expected


def test_engine_runs_a_single_rule_returning_an_empty_result_once():
    rule = FakeRule(())
    builder = SpyBuilder(RecommendationResult(recommendations=(), as_of=None))
    context = _context()

    RecommendationEngine((rule,), builder).evaluate(context)

    assert rule.contexts == [context]
    assert builder.calls == [()]


def test_engine_passes_a_single_recommendation_to_builder():
    recommendation = _recommendation(RecommendationType.EXTEND_SLEEP)
    rule = FakeRule((recommendation,))
    expected = RecommendationResult(
        recommendations=(recommendation,),
        as_of=AS_OF,
    )
    builder = SpyBuilder(expected)

    result = RecommendationEngine((rule,), builder).evaluate(_context())

    assert builder.calls == [(recommendation,)]
    assert result is expected


def test_engine_flattens_all_candidates_from_multiple_rules():
    sleep = _recommendation(
        RecommendationType.EXTEND_SLEEP,
        source_rule="SleepRule",
    )
    hydration = _recommendation(
        RecommendationType.INCREASE_HYDRATION,
        source_rule="HydrationRule",
    )
    mobility = _recommendation(
        RecommendationType.PERFORM_MOBILITY,
        source_rule="MobilityRule",
    )
    first_rule = FakeRule((sleep, hydration))
    second_rule = FakeRule((mobility,))
    expected = RecommendationResult(recommendations=(), as_of=None)
    builder = SpyBuilder(expected)
    context = _context()

    result = RecommendationEngine(
        (first_rule, second_rule),
        builder,
    ).evaluate(context)

    assert builder.calls == [(sleep, hydration, mobility)]
    assert first_rule.contexts == [context]
    assert second_rule.contexts == [context]
    assert first_rule.contexts[0] is second_rule.contexts[0]
    assert result is expected


def test_engine_result_is_independent_of_rule_order():
    sleep = _recommendation(
        RecommendationType.EXTEND_SLEEP,
        source_rule="SleepRule",
    )
    duplicate_sleep = _recommendation(
        RecommendationType.EXTEND_SLEEP,
        source_rule="RecoveryRule",
    )
    hydration = _recommendation(
        RecommendationType.INCREASE_HYDRATION,
        source_rule="HydrationRule",
    )
    rules = (
        FakeRule((sleep,)),
        FakeRule((hydration, duplicate_sleep)),
    )
    context = _context()

    forward = RecommendationEngine(rules, RecommendationBuilder()).evaluate(context)
    reversed_result = RecommendationEngine(
        tuple(reversed(rules)),
        RecommendationBuilder(),
    ).evaluate(context)

    assert forward == reversed_result


def test_engine_does_not_mutate_context():
    context = _context()
    snapshot = (
        context.decision,
        context.insights,
        context.observations,
    )
    rule = FakeRule((_recommendation(RecommendationType.PERFORM_MOBILITY),))

    RecommendationEngine((rule,), RecommendationBuilder()).evaluate(context)

    assert (
        context.decision,
        context.insights,
        context.observations,
    ) == snapshot


def test_engine_has_no_evaluation_state_and_is_deterministic():
    recommendation = _recommendation(RecommendationType.EXTEND_SLEEP)
    rule = FakeRule((recommendation,))
    engine = RecommendationEngine((rule,), RecommendationBuilder())
    context = _context()

    first = engine.evaluate(context)
    second = engine.evaluate(context)

    assert first == second
    assert rule.contexts == [context, context]


def test_engine_validates_rule_and_builder_contracts():
    with pytest.raises(TypeError, match="rules must be a tuple"):
        RecommendationEngine([], RecommendationBuilder())
    with pytest.raises(TypeError, match="every rule"):
        RecommendationEngine((object(),), RecommendationBuilder())
    with pytest.raises(TypeError, match="callable build"):
        RecommendationEngine((), object())
