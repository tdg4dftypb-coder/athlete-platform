from dataclasses import replace
from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from athlete.context_memory import (
    CoachMemoryContextBuilder,
    CoachMemoryContextRequest,
    CoachMemoryItem,
    CoachMemoryLimitation,
    DuckDbContextMemoryRepository,
    MemoryConfidence,
    MemoryDomain,
    MemoryItem,
    MemoryItemCodec,
    MemoryKind,
    MemoryLifecycleRequest,
    MemoryOrigin,
    MemoryProvenance,
    MemoryRetrievalRequest,
    MemorySensitivity,
    MemoryStatus,
    MemoryValue,
    MemoryWriteMode,
    MemoryWriteRequest,
)
from training.ingestion.source_identity import SourceIdentity


NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)


def memory_item(
    value: str,
    *,
    kind: MemoryKind = MemoryKind.PREFERENCE,
    domain: MemoryDomain = MemoryDomain.TRAINING,
    subject_id: str = "athlete:primary",
    origin: MemoryOrigin = MemoryOrigin.EXPLICIT,
    sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
    confidence: MemoryConfidence = MemoryConfidence.MEDIUM,
    valid_from: datetime = NOW - timedelta(days=1),
    valid_until: datetime | None = None,
    recorded_at: datetime = NOW - timedelta(hours=1),
    supersedes_memory_id: str | None = None,
) -> MemoryItem:
    if kind is MemoryKind.COMMITMENT:
        origin = MemoryOrigin.SYSTEM
    if kind is MemoryKind.LEARNED_PATTERN:
        origin = MemoryOrigin.INFERRED
    if kind is MemoryKind.CORRECTION:
        origin = MemoryOrigin.EXPLICIT
    if origin is MemoryOrigin.INFERRED:
        provenance = MemoryProvenance(
            "approved_memory_inference",
            f"rule-run:{value}",
            (f"evidence:{value}:2", f"evidence:{value}:1"),
            "retrieval-test-v1",
        )
        item_confidence = confidence
    elif origin is MemoryOrigin.SYSTEM:
        provenance = MemoryProvenance(
            "coach_commitment_service" if kind is MemoryKind.COMMITMENT else "system_context_service",
            f"system:{value}",
        )
        item_confidence = None
    else:
        provenance = MemoryProvenance("user", f"input:{value}")
        item_confidence = None
    return MemoryItem.create(
        subject_id=subject_id,
        kind=kind,
        domain=domain,
        payload=MemoryValue(f"{kind.value.lower()}_value", value),
        origin=origin,
        sensitivity=sensitivity,
        provenance=provenance,
        confidence=item_confidence,
        recorded_at=recorded_at,
        observed_at=(recorded_at - timedelta(hours=1) if origin is MemoryOrigin.INFERRED else None),
        valid_from=valid_from,
        valid_until=valid_until,
        supersedes_memory_id=supersedes_memory_id,
    )


def persist(repository, item: MemoryItem, *, action: str | None = None) -> MemoryItem:
    auto = item.kind in (MemoryKind.COMMITMENT, MemoryKind.LEARNED_PATTERN)
    return repository.write(
        MemoryWriteRequest(
            item=item,
            mode=MemoryWriteMode.AUTO if auto else MemoryWriteMode.EXPLICIT,
            source_identity=SourceIdentity(
                item.provenance.source_type, action or item.memory_id
            ),
            requested_at=NOW,
            explicit_authorized=not auto,
        )
    )


@pytest.fixture
def database_path(tmp_path):
    path = tmp_path / "retrieval.duckdb"
    assert "data/database" not in str(path)
    return path


@pytest.fixture
def repository(database_path):
    return DuckDbContextMemoryRepository(database_path)


def request(**changes) -> MemoryRetrievalRequest:
    values = {"subject_id": "athlete:primary", "as_of": NOW}
    values.update(changes)
    return MemoryRetrievalRequest(**values)


def context_request(**changes) -> CoachMemoryContextRequest:
    values = {"subject_id": "athlete:primary", "as_of": NOW}
    values.update(changes)
    return CoachMemoryContextRequest(**values)


def test_active_item_is_returned(repository):
    item = persist(repository, memory_item("morning"))
    assert repository.retrieve(request()).items == (item,)


def test_future_and_expired_items_are_excluded(repository):
    persist(repository, memory_item("future", valid_from=NOW + timedelta(seconds=1)))
    persist(
        repository,
        memory_item(
            "expired",
            valid_from=NOW - timedelta(days=2),
            valid_until=NOW,
        ),
    )
    assert repository.retrieve(request()).items == ()


def test_valid_until_is_half_open_for_retrieval(repository):
    before_end = persist(
        repository,
        memory_item("before-end", valid_until=NOW + timedelta(microseconds=1)),
    )
    assert repository.retrieve(request()).items == (before_end,)


def test_superseded_revoked_and_forgotten_items_are_excluded(repository):
    old = persist(repository, memory_item("old"))
    new = memory_item("new", supersedes_memory_id=old.memory_id)
    persist(repository, new)
    revoked = persist(repository, memory_item("revoked"))
    repository.revoke(
        MemoryLifecycleRequest(
            revoked.memory_id, SourceIdentity("user", "revoke"), NOW, True
        )
    )
    forgotten = persist(repository, memory_item("forgotten"))
    repository.forget(
        MemoryLifecycleRequest(
            forgotten.memory_id, SourceIdentity("user", "forget"), NOW, True
        )
    )
    ids = {item.memory_id for item in repository.retrieve(request()).items}
    assert old.memory_id not in ids
    assert revoked.memory_id not in ids
    assert forgotten.memory_id not in ids
    assert new.memory_id in ids


def test_subject_isolation_is_mandatory(repository):
    own = persist(repository, memory_item("own"))
    persist(repository, memory_item("foreign", subject_id="athlete:foreign"))
    assert repository.retrieve(request()).items == (own,)
    assert repository.retrieve(request(subject_id="athlete:foreign")).items[0].subject_id == "athlete:foreign"


def test_kind_domain_and_combined_filters(repository):
    preference = persist(repository, memory_item("training-preference"))
    goal = persist(repository, memory_item("training-goal", kind=MemoryKind.GOAL))
    lifestyle = persist(
        repository,
        memory_item("lifestyle-preference", domain=MemoryDomain.LIFESTYLE),
    )
    assert repository.list_active_by_kind(
        "athlete:primary", NOW, MemoryKind.GOAL
    ) == (goal,)
    assert set(repository.list_active_by_domain(
        "athlete:primary", NOW, MemoryDomain.TRAINING
    )) == {preference, goal}
    assert repository.list_active_by_kind_and_domain(
        "athlete:primary", NOW, MemoryKind.PREFERENCE, MemoryDomain.LIFESTYLE
    ) == (lifestyle,)


def test_convenience_category_reads_are_bounded(repository):
    items = {
        MemoryKind.PREFERENCE: memory_item("p"),
        MemoryKind.CONSTRAINT: memory_item("c", kind=MemoryKind.CONSTRAINT),
        MemoryKind.GOAL: memory_item("g", kind=MemoryKind.GOAL),
        MemoryKind.COMMITMENT: memory_item("m", kind=MemoryKind.COMMITMENT),
        MemoryKind.LEARNED_PATTERN: memory_item("l", kind=MemoryKind.LEARNED_PATTERN),
    }
    for item in items.values():
        persist(repository, item)
    assert repository.list_active_preferences("athlete:primary", NOW) == (items[MemoryKind.PREFERENCE],)
    assert repository.list_active_constraints("athlete:primary", NOW) == (items[MemoryKind.CONSTRAINT],)
    assert repository.list_active_goals("athlete:primary", NOW) == (items[MemoryKind.GOAL],)
    assert repository.list_active_commitments("athlete:primary", NOW) == (items[MemoryKind.COMMITMENT],)
    assert repository.list_active_learned_patterns("athlete:primary", NOW) == (items[MemoryKind.LEARNED_PATTERN],)


def test_sensitive_is_excluded_by_default_and_requires_explicit_retrieval_flag(repository):
    normal = persist(repository, memory_item("normal"))
    sensitive = persist(
        repository,
        memory_item("sensitive", sensitivity=MemorySensitivity.SENSITIVE),
    )
    default = repository.retrieve(request())
    assert default.items == (normal,)
    assert default.sensitive_excluded
    authorized = repository.retrieve(request(include_sensitive=True))
    assert {item.memory_id for item in authorized.items} == {
        normal.memory_id, sensitive.memory_id
    }
    assert not authorized.sensitive_excluded


def test_order_is_explicit_then_system_then_inferred(repository):
    inferred = persist(
        repository,
        memory_item("inferred", origin=MemoryOrigin.INFERRED),
    )
    system = persist(
        repository,
        memory_item("system", origin=MemoryOrigin.SYSTEM),
    )
    explicit = persist(repository, memory_item("explicit"))
    assert [item.memory_id for item in repository.retrieve(request()).items] == [
        explicit.memory_id, system.memory_id, inferred.memory_id
    ]


def test_recency_uses_valid_from_then_recorded_at(repository):
    oldest = persist(
        repository,
        memory_item("old", valid_from=NOW - timedelta(days=3), recorded_at=NOW),
    )
    middle = persist(
        repository,
        memory_item(
            "middle", valid_from=NOW - timedelta(days=2), recorded_at=NOW - timedelta(days=2)
        ),
    )
    newest = persist(
        repository,
        memory_item(
            "new", valid_from=NOW - timedelta(days=2), recorded_at=NOW - timedelta(days=1)
        ),
    )
    assert repository.retrieve(request()).items == (newest, middle, oldest)


def test_memory_id_is_final_deterministic_tie_breaker(repository):
    first = persist(repository, memory_item("alpha"))
    second = persist(repository, memory_item("beta"))
    expected = tuple(sorted((first, second), key=lambda item: item.memory_id))
    assert repository.retrieve(request()).items == expected


def test_confidence_orders_only_within_inferred_group(repository):
    low = persist(
        repository,
        memory_item("low", origin=MemoryOrigin.INFERRED, confidence=MemoryConfidence.LOW),
    )
    high = persist(
        repository,
        memory_item("high", origin=MemoryOrigin.INFERRED, confidence=MemoryConfidence.HIGH),
    )
    medium = persist(
        repository,
        memory_item("medium", origin=MemoryOrigin.INFERRED, confidence=MemoryConfidence.MEDIUM),
    )
    explicit = persist(repository, memory_item("explicit"))
    assert repository.retrieve(request()).items == (explicit, high, medium, low)


def test_retrieval_has_hard_maximum_and_reports_truncation(repository):
    for index in range(33):
        persist(repository, memory_item(f"preference-{index}"))
    result = repository.retrieve(request(limit=32))
    assert len(result.items) == 32
    assert result.truncated
    with pytest.raises(ValueError, match="between 1 and 32"):
        request(limit=33)


def test_empty_context_is_valid_and_deterministic(repository):
    builder = CoachMemoryContextBuilder(repository)
    first = builder.build(context_request())
    second = builder.build(context_request())
    assert first == second
    assert first.source_memory_ids == ()
    assert first.limitations == (CoachMemoryLimitation.NO_ACTIVE_MEMORY,)


def test_context_enforces_each_category_bound(repository):
    for index in range(9):
        persist(repository, memory_item(f"preference-{index}"))
        persist(repository, memory_item(f"constraint-{index}", kind=MemoryKind.CONSTRAINT))
    for index in range(5):
        persist(repository, memory_item(f"goal-{index}", kind=MemoryKind.GOAL))
        persist(repository, memory_item(f"pattern-{index}", kind=MemoryKind.LEARNED_PATTERN))
    for index in range(7):
        persist(repository, memory_item(f"commitment-{index}", kind=MemoryKind.COMMITMENT))
    context = CoachMemoryContextBuilder(repository).build(context_request())
    assert len(context.active_preferences) == 8
    assert len(context.active_constraints) == 8
    assert len(context.active_goals) == 4
    assert len(context.active_commitments) == 6
    assert len(context.relevant_learned_patterns) == 4
    assert CoachMemoryLimitation.MEMORY_CONTEXT_TRUNCATED in context.limitations


def test_corrections_are_bounded_and_superseded_old_state_is_absent(repository):
    for index in range(5):
        old = persist(repository, memory_item(f"old-{index}"))
        correction = memory_item(
            f"corrected-{index}",
            kind=MemoryKind.CORRECTION,
            supersedes_memory_id=old.memory_id,
        )
        persist(repository, correction)
    context = CoachMemoryContextBuilder(repository).build(context_request())
    assert len(context.recent_corrections) == 4
    assert not any("old-" in str(item.value.value) for item in context.active_preferences)


def test_global_truncation_preserves_frozen_priority(repository):
    for index in range(12):
        persist(repository, memory_item(f"preference-{index}"))
    for index in range(8):
        persist(repository, memory_item(f"constraint-{index}", kind=MemoryKind.CONSTRAINT))
    for index in range(4):
        persist(repository, memory_item(f"goal-{index}", kind=MemoryKind.GOAL))
        persist(repository, memory_item(f"pattern-{index}", kind=MemoryKind.LEARNED_PATTERN))
        old = persist(repository, memory_item(f"correct-old-{index}"))
        persist(repository, memory_item(
            f"correction-{index}", kind=MemoryKind.CORRECTION,
            supersedes_memory_id=old.memory_id,
        ))
    for index in range(6):
        persist(repository, memory_item(f"commitment-{index}", kind=MemoryKind.COMMITMENT))
    context = CoachMemoryContextBuilder(repository).build(context_request())
    assert len(context.source_memory_ids) == 32
    assert len(context.active_constraints) == 8
    assert len(context.active_goals) == 4
    assert len(context.recent_corrections) == 4
    assert len(context.active_commitments) == 6
    assert len(context.active_preferences) == 8
    assert len(context.relevant_learned_patterns) == 2
    assert CoachMemoryLimitation.MEMORY_CONTEXT_TRUNCATED in context.limitations


def test_context_domain_and_kind_request_are_honored(repository):
    training = persist(repository, memory_item("training"))
    persist(repository, memory_item("lifestyle", domain=MemoryDomain.LIFESTYLE))
    persist(repository, memory_item("goal", kind=MemoryKind.GOAL))
    context = CoachMemoryContextBuilder(repository).build(
        context_request(domains=(MemoryDomain.TRAINING,), kinds=(MemoryKind.PREFERENCE,))
    )
    assert context.source_memory_ids == (training.memory_id,)
    assert context.active_goals == ()


def test_context_sensitive_limitation_and_authorized_provenance(repository):
    sensitive = persist(repository, memory_item(
        "sensitive", sensitivity=MemorySensitivity.SENSITIVE
    ))
    default = CoachMemoryContextBuilder(repository).build(context_request())
    assert sensitive.memory_id not in default.source_memory_ids
    assert CoachMemoryLimitation.SENSITIVE_MEMORY_EXCLUDED in default.limitations
    authorized = CoachMemoryContextBuilder(repository).build(
        context_request(include_sensitive=True)
    )
    projection = authorized.active_preferences[0]
    assert projection.source_ref == "input:sensitive"
    assert projection.source_type == "user"
    assert projection.sensitivity is MemorySensitivity.SENSITIVE


def test_sensitive_projection_suppresses_source_ref_without_authorization():
    item = memory_item("sensitive", sensitivity=MemorySensitivity.SENSITIVE)
    hidden = CoachMemoryItem.from_item(item, sensitive_authorized=False)
    visible = CoachMemoryItem.from_item(item, sensitive_authorized=True)
    assert hidden.source_ref is None
    assert visible.source_ref == "input:sensitive"


def test_projection_does_not_leak_persistence_internals(repository):
    persist(repository, memory_item("normal"))
    projection = CoachMemoryContextBuilder(repository).build(
        context_request()
    ).active_preferences[0]
    assert "record_json" not in projection.__dict__
    assert "semantic_json" not in projection.__dict__
    assert "action_identity" not in projection.__dict__


def test_snapshot_and_fingerprint_are_deterministic_across_insertion_order(tmp_path):
    first_repo = DuckDbContextMemoryRepository(tmp_path / "first.duckdb")
    second_repo = DuckDbContextMemoryRepository(tmp_path / "second.duckdb")
    items = (memory_item("alpha"), memory_item("beta"), memory_item("gamma"))
    for item in items:
        persist(first_repo, item)
    for item in reversed(items):
        persist(second_repo, item)
    first = CoachMemoryContextBuilder(first_repo).build(context_request())
    second = CoachMemoryContextBuilder(second_repo).build(context_request())
    assert first == second
    assert first.fingerprint == second.fingerprint


def test_semantic_change_changes_context_fingerprint(tmp_path):
    first_repo = DuckDbContextMemoryRepository(tmp_path / "first.duckdb")
    second_repo = DuckDbContextMemoryRepository(tmp_path / "second.duckdb")
    persist(first_repo, memory_item("morning"))
    persist(second_repo, memory_item("evening"))
    first = CoachMemoryContextBuilder(first_repo).build(context_request())
    second = CoachMemoryContextBuilder(second_repo).build(context_request())
    assert first.fingerprint != second.fingerprint


def test_fingerprint_changes_with_as_of_semantics(repository):
    persist(repository, memory_item("morning"))
    builder = CoachMemoryContextBuilder(repository)
    first = builder.build(context_request(as_of=NOW))
    second = builder.build(context_request(as_of=NOW + timedelta(seconds=1)))
    assert first.fingerprint != second.fingerprint


def test_conflicting_active_replacement_chain_is_warned_and_excluded(
    repository, database_path
):
    old = persist(repository, memory_item("old"))
    new = persist(repository, memory_item("new", supersedes_memory_id=old.memory_id))
    active_old = replace(repository.get_by_id(old.memory_id), status=MemoryStatus.ACTIVE)
    connection = duckdb.connect(str(database_path))
    connection.execute(
        "UPDATE athlete_context_memory_items SET status = 'ACTIVE', record_json = ? WHERE memory_id = ?",
        [MemoryItemCodec().encode(active_old), old.memory_id],
    )
    connection.close()
    context = CoachMemoryContextBuilder(repository).build(context_request())
    assert old.memory_id not in context.source_memory_ids
    assert new.memory_id not in context.source_memory_ids
    assert CoachMemoryLimitation.INCONSISTENT_ACTIVE_MEMORY in context.limitations


def test_parameterized_subject_input_cannot_change_query_shape(repository, database_path):
    persist(repository, memory_item("normal"))
    malicious = "athlete:primary' OR 1=1 --"
    assert repository.retrieve(request(subject_id=malicious)).items == ()
    connection = duckdb.connect(str(database_path))
    assert connection.execute(
        "SELECT COUNT(*) FROM athlete_context_memory_items"
    ).fetchone() == (1,)
    connection.close()


def test_retrieval_request_requires_utc_and_canonicalizes_filters():
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        request(as_of=datetime(2026, 8, 17, 12))
    result = request(
        kinds=(MemoryKind.GOAL, MemoryKind.CONSTRAINT),
        domains=(MemoryDomain.TRAINING, MemoryDomain.HEALTH),
    )
    assert result.kinds == (MemoryKind.CONSTRAINT, MemoryKind.GOAL)
    assert result.domains == (MemoryDomain.HEALTH, MemoryDomain.TRAINING)
