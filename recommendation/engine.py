from recommendation.builder import RecommendationBuilder
from recommendation.models import (
    RecommendationContext,
    RecommendationResult,
)
from recommendation.rules import RecommendationRule


class RecommendationEngine:
    def __init__(
        self,
        rules: tuple[RecommendationRule, ...],
        builder: RecommendationBuilder,
    ) -> None:
        if not isinstance(rules, tuple):
            raise TypeError("rules must be a tuple of RecommendationRule instances")
        if not all(isinstance(rule, RecommendationRule) for rule in rules):
            raise TypeError("every rule must implement RecommendationRule")
        if not callable(getattr(builder, "build", None)):
            raise TypeError("builder must provide a callable build method")

        self._rules = rules
        self._builder = builder

    def evaluate(
        self,
        context: RecommendationContext,
    ) -> RecommendationResult:
        candidates = tuple(
            recommendation
            for rule in self._rules
            for recommendation in rule.evaluate(context)
        )
        return self._builder.build(candidates)
