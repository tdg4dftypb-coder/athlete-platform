import json
from hashlib import sha256

from recommendation.models import (
    Recommendation,
    RecommendationPriority,
    RecommendationResult,
    RecommendationType,
)


class RecommendationBuilder:
    _PRIORITY_ORDER = (
        RecommendationPriority.HIGH,
        RecommendationPriority.MEDIUM,
        RecommendationPriority.LOW,
    )
    _TYPE_ORDER = tuple(RecommendationType)

    def build(
        self,
        candidates: tuple[Recommendation, ...],
    ) -> RecommendationResult:
        grouped = {
            recommendation_type: tuple(
                candidate
                for candidate in candidates
                if candidate.type is recommendation_type
            )
            for recommendation_type in RecommendationType
            if any(
                candidate.type is recommendation_type
                for candidate in candidates
            )
        }
        recommendations = tuple(
            sorted(
                (
                    self._merge(recommendation_type, duplicates)
                    for recommendation_type, duplicates in grouped.items()
                ),
                key=self._sort_key,
            )
        )

        return RecommendationResult(
            recommendations=recommendations,
            as_of=max(
                (recommendation.as_of for recommendation in recommendations),
                default=None,
            ),
        )

    def _merge(
        self,
        recommendation_type: RecommendationType,
        candidates: tuple[Recommendation, ...],
    ) -> Recommendation:
        evidence = tuple(
            sorted(
                {
                    item
                    for candidate in candidates
                    for item in candidate.evidence
                }
            )
        )
        source_rules = tuple(
            sorted(
                {
                    source_rule
                    for candidate in candidates
                    for source_rule in candidate.source_rules
                }
            )
        )

        return Recommendation(
            id=self._build_id(
                recommendation_type,
                evidence,
                source_rules,
            ),
            type=recommendation_type,
            priority=min(
                (candidate.priority for candidate in candidates),
                key=self._PRIORITY_ORDER.index,
            ),
            confidence=max(candidate.confidence for candidate in candidates),
            evidence=evidence,
            source_rules=source_rules,
            as_of=max(candidate.as_of for candidate in candidates),
        )

    def _sort_key(
        self,
        recommendation: Recommendation,
    ) -> tuple[int, int, str]:
        return (
            self._PRIORITY_ORDER.index(recommendation.priority),
            self._TYPE_ORDER.index(recommendation.type),
            recommendation.id,
        )

    @staticmethod
    def _build_id(
        recommendation_type: RecommendationType,
        evidence: tuple[str, ...],
        source_rules: tuple[str, ...],
    ) -> str:
        identity = json.dumps(
            [recommendation_type.value, evidence, source_rules],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = sha256(identity).hexdigest()
        return f"{recommendation_type.value}:sha256:{digest}"
