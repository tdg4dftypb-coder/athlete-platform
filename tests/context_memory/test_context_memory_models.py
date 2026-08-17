from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from athlete.context_memory import (
    DEFAULT_SUBJECT_ID,
    MAX_EVIDENCE_REFS,
    ForgottenMemoryTombstone,
    MemoryAttribute,
    MemoryConfidence,
    MemoryDomain,
    MemoryItem,
    MemoryKind,
    MemoryOrigin,
    MemoryProvenance,
    MemorySensitivity,
    MemoryStatus,
    MemoryValue,
)


NOW = datetime(2026, 8, 17, 8, tzinfo=timezone.utc)
PREVIOUS_ID = "memory:sha256:" + "a" * 64


def explicit_item(**changes) -> MemoryItem:
    values = {
        "kind": MemoryKind.PREFERENCE,
        "domain": MemoryDomain.TRAINING,
        "payload": MemoryValue("preferred_training_time", "morning"),
        "origin": MemoryOrigin.EXPLICIT,
        "sensitivity": MemorySensitivity.NORMAL,
        "provenance": MemoryProvenance("user", "conversation:42"),
        "recorded_at": NOW,
        "valid_from": NOW,
    }
    values.update(changes)
    return MemoryItem.create(**values)


def inferred_item(**changes) -> MemoryItem:
    values = {
        "kind": MemoryKind.LEARNED_PATTERN,
        "domain": MemoryDomain.TRAINING,
        "payload": MemoryValue("long_ride_tolerance", "better_after_rest_day"),
        "origin": MemoryOrigin.INFERRED,
        "sensitivity": MemorySensitivity.NORMAL,
        "provenance": MemoryProvenance(
            "deterministic_rule",
            evidence_refs=("activity:2", "activity:1"),
            inference_rule_version="ride-tolerance-v1",
        ),
        "confidence": MemoryConfidence.MEDIUM,
        "recorded_at": NOW,
        "observed_at": NOW - timedelta(days=1),
        "valid_from": NOW,
    }
    values.update(changes)
    return MemoryItem.create(**values)


def test_models_are_immutable_and_default_subject_is_explicit():
    item = explicit_item()
    assert item.subject_id == DEFAULT_SUBJECT_ID == "athlete:primary"
    with pytest.raises(FrozenInstanceError):
        item.status = MemoryStatus.REVOKED


def test_same_semantics_produce_same_identity_despite_recording_time():
    first = explicit_item()
    second = explicit_item(recorded_at=NOW + timedelta(minutes=1))
    assert first.memory_id == second.memory_id


@pytest.mark.parametrize(
    "change",
    [
        {"payload": MemoryValue("preferred_training_time", "evening")},
        {"domain": MemoryDomain.LIFESTYLE},
        {"sensitivity": MemorySensitivity.SENSITIVE},
        {"valid_from": NOW + timedelta(days=1)},
    ],
)
def test_meaningful_semantic_change_changes_identity(change):
    assert explicit_item().memory_id != explicit_item(**change).memory_id


def test_attribute_and_evidence_order_are_canonical_for_identity():
    attrs = (
        MemoryAttribute("weekday", "monday"),
        MemoryAttribute("period", "morning"),
    )
    first = explicit_item(
        payload=MemoryValue("training_window", "preferred", attrs),
        provenance=MemoryProvenance(
            "operator", evidence_refs=("input:2", "input:1")
        ),
    )
    second = explicit_item(
        payload=MemoryValue("training_window", "preferred", tuple(reversed(attrs))),
        provenance=MemoryProvenance(
            "operator", evidence_refs=("input:1", "input:2")
        ),
    )
    assert first.memory_id == second.memory_id
    assert tuple(item.key for item in first.payload.attributes) == ("period", "weekday")
    assert first.provenance.evidence_refs == ("input:1", "input:2")


def test_explicit_is_valid_without_confidence():
    assert explicit_item().origin is MemoryOrigin.EXPLICIT


def test_explicit_with_confidence_is_invalid():
    with pytest.raises(ValueError, match="confidence is allowed only"):
        explicit_item(confidence=MemoryConfidence.HIGH)


def test_inferred_is_valid_with_bounded_confidence_rule_and_evidence():
    item = inferred_item()
    assert item.confidence is MemoryConfidence.MEDIUM


def test_inferred_without_confidence_is_invalid():
    with pytest.raises(ValueError, match="requires confidence"):
        inferred_item(confidence=None)


def test_inferred_without_rule_version_is_invalid():
    with pytest.raises(ValueError, match="requires inference_rule_version"):
        inferred_item(
            provenance=MemoryProvenance(
                "deterministic_rule", evidence_refs=("a", "b")
            )
        )


def test_inferred_without_evidence_is_invalid():
    with pytest.raises(ValueError, match="requires evidence_refs"):
        inferred_item(
            provenance=MemoryProvenance(
                "deterministic_rule", inference_rule_version="v1"
            )
        )


def test_system_commitment_is_valid_without_confidence():
    item = explicit_item(
        kind=MemoryKind.COMMITMENT,
        origin=MemoryOrigin.SYSTEM,
        payload=MemoryValue("coach_commitment", "review_training_load_next_week"),
        provenance=MemoryProvenance("coach_workflow", "commitment:1"),
    )
    assert item.origin is MemoryOrigin.SYSTEM


def test_system_with_confidence_is_invalid():
    with pytest.raises(ValueError, match="confidence is allowed only"):
        explicit_item(
            kind=MemoryKind.COMMITMENT,
            origin=MemoryOrigin.SYSTEM,
            confidence=MemoryConfidence.LOW,
            provenance=MemoryProvenance("coach_workflow"),
        )


def test_active_item_can_transition_to_each_terminal_status_without_new_identity():
    item = explicit_item()
    for status in (
        MemoryStatus.SUPERSEDED,
        MemoryStatus.REVOKED,
        MemoryStatus.FORGOTTEN,
    ):
        transitioned = item.transition_to(status)
        assert transitioned.status is status
        assert transitioned.memory_id == item.memory_id
        assert item.status is MemoryStatus.ACTIVE


@pytest.mark.parametrize(
    "initial",
    [MemoryStatus.SUPERSEDED, MemoryStatus.REVOKED, MemoryStatus.FORGOTTEN],
)
def test_terminal_item_cannot_be_reactivated(initial):
    item = explicit_item(status=initial)
    with pytest.raises(ValueError, match="illegal memory lifecycle transition"):
        item.transition_to(MemoryStatus.ACTIVE)


def test_active_to_active_transition_is_rejected():
    with pytest.raises(ValueError, match="illegal memory lifecycle transition"):
        explicit_item().transition_to(MemoryStatus.ACTIVE)


def test_superseding_self_is_invalid():
    item = explicit_item()
    with pytest.raises(ValueError, match="cannot supersede itself"):
        MemoryItem(
            **{
                **item.__dict__,
                "supersedes_memory_id": item.memory_id,
            }
        )


def test_new_item_can_represent_supersession_without_mutating_previous_item():
    previous = explicit_item()
    current = explicit_item(
        payload=MemoryValue("preferred_training_time", "evening"),
        supersedes_memory_id=previous.memory_id,
    )
    assert current.supersedes_memory_id == previous.memory_id
    assert previous.status is MemoryStatus.ACTIVE


def test_revoked_item_keeps_historical_payload():
    revoked = explicit_item().transition_to(MemoryStatus.REVOKED)
    assert revoked.payload.value == "morning"


def test_forgotten_tombstone_contains_no_payload_or_evidence():
    item = explicit_item().transition_to(MemoryStatus.FORGOTTEN)
    tombstone = ForgottenMemoryTombstone(item.memory_id, item.subject_id, NOW)
    assert set(tombstone.__dict__) == {"memory_id", "subject_id", "forgotten_at"}


def test_active_half_open_temporal_semantics():
    item = explicit_item(valid_until=NOW + timedelta(days=1))
    assert not item.is_active(NOW - timedelta(microseconds=1))
    assert item.is_active(NOW)
    assert item.is_active(NOW + timedelta(days=1, microseconds=-1))
    assert not item.is_active(NOW + timedelta(days=1))


def test_non_active_lifecycle_status_is_never_active():
    assert not explicit_item(status=MemoryStatus.REVOKED).is_active(NOW)


@pytest.mark.parametrize("offset", [timedelta(0), -timedelta(seconds=1)])
def test_valid_until_must_be_strictly_after_valid_from(offset):
    with pytest.raises(ValueError, match="valid_until must be after"):
        explicit_item(valid_until=NOW + offset)


@pytest.mark.parametrize("field", ["recorded_at", "valid_from", "observed_at", "valid_until"])
def test_temporal_values_must_be_timezone_aware_utc(field):
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        explicit_item(**{field: datetime(2026, 8, 17, 8)})


def test_non_utc_offset_is_rejected():
    with pytest.raises(ValueError, match="must use UTC"):
        explicit_item(recorded_at=NOW.astimezone(timezone(timedelta(hours=2))))


def test_observed_at_cannot_be_after_recorded_at():
    with pytest.raises(ValueError, match="observed_at cannot be after"):
        inferred_item(observed_at=NOW + timedelta(seconds=1))


def test_all_six_memory_kinds_are_frozen():
    assert {item.value for item in MemoryKind} == {
        "PREFERENCE", "CONSTRAINT", "GOAL", "CORRECTION", "COMMITMENT", "LEARNED_PATTERN"
    }


def test_all_six_memory_domains_are_frozen():
    assert {item.value for item in MemoryDomain} == {
        "TRAINING", "RECOVERY", "HEALTH", "LIFESTYLE", "EQUIPMENT", "NUTRITION"
    }


def test_evidence_refs_are_bounded_to_sixteen():
    provenance = MemoryProvenance(
        "rule", evidence_refs=tuple(f"evidence:{index}" for index in range(MAX_EVIDENCE_REFS))
    )
    assert len(provenance.evidence_refs) == 16


def test_too_many_evidence_refs_are_rejected():
    with pytest.raises(ValueError, match="cannot contain more than 16"):
        MemoryProvenance(
            "rule",
            evidence_refs=tuple(f"evidence:{index}" for index in range(MAX_EVIDENCE_REFS + 1)),
        )


def test_empty_and_duplicate_evidence_refs_are_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        MemoryProvenance("rule", evidence_refs=("",))
    with pytest.raises(ValueError, match="unique"):
        MemoryProvenance("rule", evidence_refs=("same", "same"))


def test_learned_pattern_must_be_inferred():
    with pytest.raises(ValueError, match="LEARNED_PATTERN must be INFERRED"):
        explicit_item(kind=MemoryKind.LEARNED_PATTERN)


def test_learned_pattern_rejects_one_evidence_reference():
    with pytest.raises(ValueError, match="at least two"):
        inferred_item(
            provenance=MemoryProvenance(
                "rule", evidence_refs=("activity:1",), inference_rule_version="v1"
            )
        )


def test_learned_pattern_accepts_two_evidence_references():
    assert len(inferred_item().provenance.evidence_refs) == 2


@pytest.mark.parametrize("value", ["morning", True, 3, 3.5])
def test_payload_accepts_bounded_scalar_and_structured_values(value):
    payload = MemoryValue(
        "preference",
        value,
        (MemoryAttribute("priority", 2), MemoryAttribute("stable", True)),
    )
    assert len(payload.attributes) == 2


def test_payload_rejects_oversized_text_and_structure():
    with pytest.raises(ValueError, match="maximum length 512"):
        MemoryValue("preference", "x" * 513)
    with pytest.raises(ValueError, match="more than 8"):
        MemoryValue(
            "preference",
            "morning",
            tuple(MemoryAttribute(f"key{index}", index) for index in range(9)),
        )


@pytest.mark.parametrize(
    "key", ["transcript", "conversation", "conversation_history", "messages", "raw_conversation"]
)
def test_raw_conversation_payload_keys_are_rejected(key):
    with pytest.raises(ValueError, match="conversation transcript"):
        MemoryValue(key, "raw text")


def test_normal_and_sensitive_classification_have_no_lifecycle_side_effects():
    normal = explicit_item(sensitivity=MemorySensitivity.NORMAL)
    sensitive = explicit_item(sensitivity=MemorySensitivity.SENSITIVE)
    assert normal.status is sensitive.status is MemoryStatus.ACTIVE
    assert normal.origin is sensitive.origin is MemoryOrigin.EXPLICIT


def test_explicit_correction_references_previous_memory():
    correction = explicit_item(
        kind=MemoryKind.CORRECTION,
        payload=MemoryValue("preferred_training_time", "evening_not_morning"),
        supersedes_memory_id=PREVIOUS_ID,
    )
    assert correction.supersedes_memory_id == PREVIOUS_ID


def test_correction_requires_explicit_origin_and_reference():
    with pytest.raises(ValueError, match="must reference"):
        explicit_item(kind=MemoryKind.CORRECTION)
    with pytest.raises(ValueError, match="must be EXPLICIT"):
        explicit_item(
            kind=MemoryKind.CORRECTION,
            origin=MemoryOrigin.SYSTEM,
            supersedes_memory_id=PREVIOUS_ID,
            provenance=MemoryProvenance("system"),
        )


def test_commitment_is_system_originated_and_not_a_scheduler_contract():
    commitment = explicit_item(
        kind=MemoryKind.COMMITMENT,
        origin=MemoryOrigin.SYSTEM,
        payload=MemoryValue("coach_commitment", "revisit_goal_next_check_in"),
        provenance=MemoryProvenance("coach"),
    )
    assert commitment.kind is MemoryKind.COMMITMENT
    with pytest.raises(ValueError, match="must be SYSTEM-originated"):
        explicit_item(kind=MemoryKind.COMMITMENT)
