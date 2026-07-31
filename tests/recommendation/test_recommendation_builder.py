from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from hashlib import sha256
import json

import pytest

from recommendation import (
    Recommendation,
    RecommendationBuilder,
    RecommendationPriority,
    RecommendationType,
)


AS_OF = datetime(2026, 7, 31, 8)


def _candidate(
    recommendation_type: RecommendationType,
    *,
    priority: RecommendationPriority = RecommendationPriority.MEDIUM,
    confidence: float = 0.7,
    evidence: tuple[str, ...] = ("event-1",),
    source_rules: tuple[str, ...] = ("RuleA",),
    as_of: datetime = AS_OF,
    candidate_id: str = "candidate-id",
) -> Recommendation:
    return Recommendation(
        id=candidate_id,
        type=recommendation_type,
        priority=priority,
        confidence=confidence,
        evidence=evidence,
        source_rules=source_rules,
        as_of=as_of,
    )


def _expected_id(
    recommendation_type: RecommendationType,
    evidence: tuple[str, ...],
    source_rules: tuple[str, ...],
) -> str:
    identity = json.dumps(
        [recommendation_type.value, evidence, source_rules],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{recommendation_type.value}:sha256:{sha256(identity).hexdigest()}"


def test_builder_returns_an_immutable_empty_result_without_a_timestamp():
    result = RecommendationBuilder().build(())

    assert result.recommendations == ()
    assert result.as_of is None
    with pytest.raises(FrozenInstanceError):
        result.as_of = AS_OF


def test_builder_normalizes_a_single_recommendation():
    candidate = _candidate(RecommendationType.EXTEND_SLEEP)

    result = RecommendationBuilder().build((candidate,))

    assert len(result.recommendations) == 1
    recommendation = result.recommendations[0]
    assert recommendation.type is RecommendationType.EXTEND_SLEEP
    assert recommendation.priority is RecommendationPriority.MEDIUM
    assert recommendation.confidence == 0.7
    assert recommendation.evidence == ("event-1",)
    assert recommendation.source_rules == ("RuleA",)
    assert recommendation.as_of == AS_OF
    assert recommendation.id == _expected_id(
        RecommendationType.EXTEND_SLEEP,
        ("event-1",),
        ("RuleA",),
    )
    assert result.as_of == AS_OF


def test_builder_keeps_different_recommendation_types_separate():
    candidates = (
        _candidate(RecommendationType.PERFORM_MOBILITY),
        _candidate(RecommendationType.INCREASE_HYDRATION),
        _candidate(RecommendationType.EXTEND_SLEEP),
    )

    result = RecommendationBuilder().build(candidates)

    assert {item.type for item in result.recommendations} == {
        RecommendationType.EXTEND_SLEEP,
        RecommendationType.INCREASE_HYDRATION,
        RecommendationType.PERFORM_MOBILITY,
    }


def test_builder_merges_duplicates_by_type():
    later = AS_OF + timedelta(hours=2)
    candidates = (
        _candidate(
            RecommendationType.APPLY_RECOVERY_PROTOCOL,
            priority=RecommendationPriority.LOW,
            confidence=0.6,
            evidence=("event-b", "event-a"),
            source_rules=("RuleB",),
        ),
        _candidate(
            RecommendationType.APPLY_RECOVERY_PROTOCOL,
            priority=RecommendationPriority.HIGH,
            confidence=0.9,
            evidence=("event-c", "event-a"),
            source_rules=("RuleC", "RuleA"),
            as_of=later,
        ),
    )

    result = RecommendationBuilder().build(candidates)

    assert len(result.recommendations) == 1
    recommendation = result.recommendations[0]
    assert recommendation.priority is RecommendationPriority.HIGH
    assert recommendation.confidence == 0.9
    assert recommendation.evidence == ("event-a", "event-b", "event-c")
    assert recommendation.source_rules == ("RuleA", "RuleB", "RuleC")
    assert recommendation.as_of == later
    assert result.as_of == later
    assert recommendation.id == _expected_id(
        RecommendationType.APPLY_RECOVERY_PROTOCOL,
        ("event-a", "event-b", "event-c"),
        ("RuleA", "RuleB", "RuleC"),
    )


def test_builder_sorts_by_priority_then_type():
    candidates = (
        _candidate(
            RecommendationType.PERFORM_MOBILITY,
            priority=RecommendationPriority.MEDIUM,
        ),
        _candidate(
            RecommendationType.INCREASE_HYDRATION,
            priority=RecommendationPriority.HIGH,
        ),
        _candidate(
            RecommendationType.EXTEND_SLEEP,
            priority=RecommendationPriority.HIGH,
        ),
        _candidate(
            RecommendationType.APPLY_RECOVERY_PROTOCOL,
            priority=RecommendationPriority.LOW,
        ),
    )

    result = RecommendationBuilder().build(candidates)

    assert tuple(item.type for item in result.recommendations) == (
        RecommendationType.EXTEND_SLEEP,
        RecommendationType.INCREASE_HYDRATION,
        RecommendationType.PERFORM_MOBILITY,
        RecommendationType.APPLY_RECOVERY_PROTOCOL,
    )


def test_builder_is_independent_of_candidate_order():
    candidates = (
        _candidate(
            RecommendationType.EXTEND_SLEEP,
            evidence=("event-b",),
            source_rules=("RuleB",),
        ),
        _candidate(
            RecommendationType.INCREASE_HYDRATION,
            priority=RecommendationPriority.HIGH,
        ),
        _candidate(
            RecommendationType.EXTEND_SLEEP,
            priority=RecommendationPriority.HIGH,
            evidence=("event-a",),
            source_rules=("RuleA",),
        ),
    )

    forward = RecommendationBuilder().build(candidates)
    reversed_result = RecommendationBuilder().build(tuple(reversed(candidates)))

    assert forward == reversed_result


def test_builder_does_not_mutate_input_candidates():
    candidates = (
        _candidate(
            RecommendationType.EXTEND_SLEEP,
            evidence=("event-b", "event-a"),
            source_rules=("RuleB", "RuleA"),
        ),
        _candidate(
            RecommendationType.EXTEND_SLEEP,
            priority=RecommendationPriority.HIGH,
        ),
    )
    snapshot = tuple(candidates)

    RecommendationBuilder().build(candidates)

    assert candidates == snapshot
    assert candidates[0].evidence == ("event-b", "event-a")
    assert candidates[0].source_rules == ("RuleB", "RuleA")


def test_result_as_of_is_latest_across_different_recommendations():
    later = AS_OF + timedelta(days=1)
    candidates = (
        _candidate(RecommendationType.EXTEND_SLEEP, as_of=AS_OF),
        _candidate(RecommendationType.PERFORM_MOBILITY, as_of=later),
    )

    result = RecommendationBuilder().build(candidates)

    assert result.as_of == later
