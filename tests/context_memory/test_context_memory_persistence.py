from datetime import datetime, timedelta, timezone
import json

import duckdb
import pytest

from athlete.context_memory import (
    AthleteContextMemorySchema,
    DeterministicMemoryWritePolicy,
    DuckDbContextMemoryRepository,
    ExplicitAuthorizationRequiredError,
    ForgottenMemoryReplayError,
    IllegalMemoryLifecycleTransitionError,
    MemoryAttribute,
    MemoryCollisionError,
    MemoryConfidence,
    MemoryDomain,
    MemoryItem,
    MemoryItemCodec,
    MemoryKind,
    MemoryLifecycleRequest,
    MemoryNotFoundError,
    MemoryOrigin,
    MemoryProvenance,
    MemorySensitivity,
    MemoryStatus,
    MemoryValue,
    MemoryWriteDecision,
    MemoryWriteMode,
    MemoryWriteRejectedError,
    MemoryWriteRequest,
    get_default_context_memory_db_path,
)
from training.ingestion.source_identity import SourceIdentity


NOW = datetime(2026, 8, 17, 10, tzinfo=timezone.utc)


def explicit_item(**changes) -> MemoryItem:
    values = {
        "kind": MemoryKind.PREFERENCE,
        "domain": MemoryDomain.TRAINING,
        "payload": MemoryValue(
            "preferred_training_time",
            "morning",
            (MemoryAttribute("weekday", "monday"),),
        ),
        "origin": MemoryOrigin.EXPLICIT,
        "sensitivity": MemorySensitivity.NORMAL,
        "provenance": MemoryProvenance(
            "user", "operator-input:1", ("input:2", "input:1")
        ),
        "recorded_at": NOW,
        "valid_from": NOW,
    }
    values.update(changes)
    return MemoryItem.create(**values)


def inferred_pattern(**changes) -> MemoryItem:
    values = {
        "kind": MemoryKind.LEARNED_PATTERN,
        "domain": MemoryDomain.TRAINING,
        "payload": MemoryValue("ride_tolerance", "better_after_rest"),
        "origin": MemoryOrigin.INFERRED,
        "sensitivity": MemorySensitivity.NORMAL,
        "provenance": MemoryProvenance(
            "approved_memory_inference",
            "rule-run:1",
            ("activity:2", "activity:1"),
            "ride-pattern-v1",
        ),
        "confidence": MemoryConfidence.HIGH,
        "recorded_at": NOW,
        "observed_at": NOW - timedelta(days=1),
        "valid_from": NOW,
    }
    values.update(changes)
    return MemoryItem.create(**values)


def commitment(**changes) -> MemoryItem:
    values = {
        "kind": MemoryKind.COMMITMENT,
        "domain": MemoryDomain.TRAINING,
        "payload": MemoryValue("coach_commitment", "review_goal_next_check_in"),
        "origin": MemoryOrigin.SYSTEM,
        "sensitivity": MemorySensitivity.NORMAL,
        "provenance": MemoryProvenance(
            "coach_commitment_service", "workflow:1"
        ),
        "recorded_at": NOW,
        "valid_from": NOW,
    }
    values.update(changes)
    return MemoryItem.create(**values)


def write_request(
    item: MemoryItem,
    *,
    action: str = "write-1",
    mode: MemoryWriteMode = MemoryWriteMode.EXPLICIT,
    authorized: bool = True,
) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        item=item,
        mode=mode,
        source_identity=SourceIdentity(item.provenance.source_type, action),
        requested_at=NOW,
        explicit_authorized=authorized,
    )


def lifecycle_request(
    memory_id: str, *, action: str, authorized: bool = True
) -> MemoryLifecycleRequest:
    return MemoryLifecycleRequest(
        memory_id=memory_id,
        source_identity=SourceIdentity("user", action),
        requested_at=NOW + timedelta(minutes=1),
        explicit_authorized=authorized,
    )


@pytest.fixture
def database_path(tmp_path):
    path = tmp_path / "context-memory.duckdb"
    assert "data/database" not in str(path)
    return path


@pytest.fixture
def repository(database_path):
    return DuckDbContextMemoryRepository(database_path)


def table_names(path) -> set[str]:
    connection = duckdb.connect(str(path))
    try:
        return {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
    finally:
        connection.close()


def test_schema_creates_three_separate_context_memory_tables(database_path):
    DuckDbContextMemoryRepository(database_path)
    assert {
        "athlete_context_memory_items",
        "athlete_context_memory_tombstones",
        "athlete_context_memory_actions",
    } <= table_names(database_path)


def test_context_memory_path_uses_canonical_health_database_without_opening_it(
    monkeypatch, tmp_path
):
    target = tmp_path / "explicit-health.duckdb"
    monkeypatch.setenv("HEALTH_DB_PATH", str(target))
    assert get_default_context_memory_db_path() == target
    assert not target.exists()


def test_schema_creation_is_idempotent(database_path):
    repository = DuckDbContextMemoryRepository(database_path)
    repository.initialize_schema()
    repository.initialize_schema()
    assert "athlete_context_memory_items" in table_names(database_path)


def test_schema_does_not_modify_existing_activity_memory_table(database_path):
    connection = duckdb.connect(str(database_path))
    connection.execute("CREATE TABLE athlete_memory_events (event_id VARCHAR PRIMARY KEY)")
    connection.execute("INSERT INTO athlete_memory_events VALUES ('existing-event')")
    AthleteContextMemorySchema.create(connection)
    AthleteContextMemorySchema.create(connection)
    assert connection.execute("SELECT * FROM athlete_memory_events").fetchall() == [
        ("existing-event",)
    ]
    connection.close()


@pytest.mark.parametrize(
    "item",
    [
        explicit_item(),
        inferred_pattern(),
        explicit_item(
            domain=MemoryDomain.HEALTH,
            sensitivity=MemorySensitivity.SENSITIVE,
            payload=MemoryValue("medical_constraint", "operator_confirmed"),
        ),
    ],
)
def test_codec_round_trip_preserves_full_semantics(item):
    codec = MemoryItemCodec()
    assert codec.decode(codec.encode(item)) == item


def test_codec_output_is_canonical_and_preserves_evidence_order():
    item = explicit_item()
    encoded = MemoryItemCodec().encode(item)
    assert encoded == MemoryItemCodec().encode(item)
    data = json.loads(encoded)
    assert data["provenance"]["evidence_refs"] == ["input:1", "input:2"]
    assert "MemoryKind" not in encoded


def test_insert_and_get_by_id(repository):
    item = explicit_item()
    assert repository.write(write_request(item)) == item
    assert repository.get_by_id(item.memory_id) == item
    assert repository.exists(item.memory_id)


def test_identical_semantic_write_is_idempotent(repository):
    first = explicit_item()
    retry = explicit_item(recorded_at=NOW + timedelta(seconds=30))
    stored = repository.write(write_request(first))
    retried = repository.write(write_request(retry, action="retry-2"))
    assert retried == stored
    assert retried.recorded_at == NOW


def test_same_memory_id_with_different_persisted_semantics_is_collision(
    repository, database_path
):
    item = explicit_item()
    repository.write(write_request(item))
    connection = duckdb.connect(str(database_path))
    connection.execute(
        "UPDATE athlete_context_memory_items SET semantic_json = '{}' WHERE memory_id = ?",
        [item.memory_id],
    )
    connection.close()
    with pytest.raises(MemoryCollisionError, match="different semantic content"):
        repository.write(write_request(item, action="collision-check"))


def test_source_action_identity_collision_is_explicit(repository):
    first = explicit_item()
    second = explicit_item(payload=MemoryValue("preferred_training_time", "evening"))
    repository.write(write_request(first, action="same-action"))
    with pytest.raises(MemoryCollisionError, match="source action identity collision"):
        repository.write(write_request(second, action="same-action"))


def test_atomic_supersession_marks_old_and_inserts_new(repository):
    old = explicit_item()
    repository.write(write_request(old))
    new = explicit_item(
        payload=MemoryValue("preferred_training_time", "evening"),
        supersedes_memory_id=old.memory_id,
    )
    repository.write(write_request(new, action="supersede-1"))
    assert repository.get_by_id(old.memory_id).status is MemoryStatus.SUPERSEDED
    assert repository.get_by_id(new.memory_id).status is MemoryStatus.ACTIVE
    assert repository.get_by_id(old.memory_id).memory_id == old.memory_id


def test_correction_can_supersede_different_kind_in_same_domain(repository):
    old = explicit_item()
    repository.write(write_request(old))
    correction = explicit_item(
        kind=MemoryKind.CORRECTION,
        payload=MemoryValue("preferred_training_time", "evening_not_morning"),
        supersedes_memory_id=old.memory_id,
    )
    repository.write(write_request(correction, action="correction-1"))
    assert repository.get_by_id(old.memory_id).status is MemoryStatus.SUPERSEDED


def test_missing_superseded_item_rolls_back_new_item(repository):
    new = explicit_item(
        payload=MemoryValue("preferred_training_time", "evening"),
        supersedes_memory_id="memory:sha256:" + "a" * 64,
    )
    with pytest.raises(MemoryNotFoundError):
        repository.write(write_request(new))
    assert not repository.exists(new.memory_id)


def test_non_active_old_item_rejects_supersession_and_rolls_back(repository):
    old = explicit_item()
    repository.write(write_request(old))
    repository.revoke(lifecycle_request(old.memory_id, action="revoke-old"))
    new = explicit_item(
        payload=MemoryValue("preferred_training_time", "evening"),
        supersedes_memory_id=old.memory_id,
    )
    with pytest.raises(IllegalMemoryLifecycleTransitionError):
        repository.write(write_request(new, action="supersede-revoked"))
    assert not repository.exists(new.memory_id)


@pytest.mark.parametrize(
    "change",
    [
        {"kind": MemoryKind.GOAL},
        {"domain": MemoryDomain.LIFESTYLE},
    ],
)
def test_incompatible_supersession_rolls_back(change, repository):
    old = explicit_item()
    repository.write(write_request(old))
    new = explicit_item(
        **change,
        payload=MemoryValue("replacement", "different"),
        supersedes_memory_id=old.memory_id,
    )
    with pytest.raises(MemoryCollisionError, match="kind/domain mismatch"):
        repository.write(write_request(new, action=f"bad-{next(iter(change))}"))
    assert not repository.exists(new.memory_id)
    assert repository.get_by_id(old.memory_id).status is MemoryStatus.ACTIVE


def test_active_revoke_and_repeated_revoke_are_idempotent(repository):
    item = explicit_item()
    repository.write(write_request(item))
    first = repository.revoke(lifecycle_request(item.memory_id, action="revoke-1"))
    second = repository.revoke(lifecycle_request(item.memory_id, action="revoke-2"))
    assert first.status is second.status is MemoryStatus.REVOKED
    assert first.memory_id == second.memory_id == item.memory_id


def test_revoke_requires_authorization(repository):
    item = explicit_item()
    repository.write(write_request(item))
    with pytest.raises(ExplicitAuthorizationRequiredError):
        repository.revoke(
            lifecycle_request(item.memory_id, action="revoke-no-auth", authorized=False)
        )


def test_revoke_missing_or_incompatible_terminal_is_rejected(repository):
    with pytest.raises(MemoryNotFoundError):
        repository.revoke(lifecycle_request("missing", action="missing"))
    old = explicit_item()
    repository.write(write_request(old))
    new = explicit_item(
        payload=MemoryValue("preferred_training_time", "evening"),
        supersedes_memory_id=old.memory_id,
    )
    repository.write(write_request(new, action="supersede"))
    with pytest.raises(IllegalMemoryLifecycleTransitionError):
        repository.revoke(lifecycle_request(old.memory_id, action="revoke-superseded"))


def test_forget_removes_original_row_and_keeps_minimal_tombstone(
    repository, database_path
):
    item = explicit_item(
        sensitivity=MemorySensitivity.SENSITIVE,
        payload=MemoryValue("medical_constraint", "sensitive-original-text"),
        provenance=MemoryProvenance(
            "user", "sensitive-source-ref", ("sensitive-evidence",)
        ),
    )
    repository.write(write_request(item))
    tombstone = repository.forget(lifecycle_request(item.memory_id, action="forget-1"))
    assert repository.get_by_id(item.memory_id) is None
    assert repository.get_tombstone(item.memory_id) == tombstone
    assert set(tombstone.__dict__) == {"memory_id", "subject_id", "forgotten_at"}
    connection = duckdb.connect(str(database_path))
    assert connection.execute(
        "SELECT COUNT(*) FROM athlete_context_memory_items WHERE memory_id = ?",
        [item.memory_id],
    ).fetchone() == (0,)
    assert [row[1] for row in connection.execute(
        "PRAGMA table_info('athlete_context_memory_tombstones')"
    ).fetchall()] == ["memory_id", "subject_id", "forgotten_at"]
    connection.close()


def test_repeated_forget_is_idempotent(repository):
    item = explicit_item()
    repository.write(write_request(item))
    first = repository.forget(lifecycle_request(item.memory_id, action="forget-1"))
    second = repository.forget(lifecycle_request(item.memory_id, action="forget-2"))
    assert first == second


def test_forgotten_item_replay_is_blocked(repository):
    item = explicit_item()
    repository.write(write_request(item))
    repository.forget(lifecycle_request(item.memory_id, action="forget"))
    with pytest.raises(ForgottenMemoryReplayError):
        repository.write(write_request(item, action="replay"))


def test_forget_requires_authorization(repository):
    item = explicit_item()
    repository.write(write_request(item))
    with pytest.raises(ExplicitAuthorizationRequiredError):
        repository.forget(
            lifecycle_request(item.memory_id, action="forget-no-auth", authorized=False)
        )


def test_forget_transaction_rolls_back_tombstone_if_delete_fails(
    repository, monkeypatch
):
    item = explicit_item()
    repository.write(write_request(item))

    def fail_delete(connection, memory_id):
        raise RuntimeError("injected delete failure")

    monkeypatch.setattr(repository, "_delete_item_in_transaction", fail_delete)
    with pytest.raises(RuntimeError, match="injected"):
        repository.forget(lifecycle_request(item.memory_id, action="forget-fail"))
    assert repository.get_by_id(item.memory_id) == item
    assert repository.get_tombstone(item.memory_id) is None


def test_explicit_preference_without_authorization_is_blocked(repository):
    with pytest.raises(ExplicitAuthorizationRequiredError):
        repository.write(write_request(explicit_item(), authorized=False))


def test_explicit_preference_with_authorization_is_allowed(repository):
    item = explicit_item()
    assert repository.write(write_request(item)).memory_id == item.memory_id


def test_sensitive_without_authorization_is_blocked(repository):
    item = explicit_item(sensitivity=MemorySensitivity.SENSITIVE)
    with pytest.raises(ExplicitAuthorizationRequiredError):
        repository.write(write_request(item, authorized=False))


def test_sensitive_inferred_is_always_rejected(repository):
    item = inferred_pattern(sensitivity=MemorySensitivity.SENSITIVE)
    with pytest.raises(MemoryWriteRejectedError, match="SENSITIVE_INFERENCE_FORBIDDEN"):
        repository.write(write_request(item, action="sensitive-inference"))


def test_approved_system_commitment_can_auto_store(repository):
    item = commitment()
    request = write_request(
        item, action="commitment-1", mode=MemoryWriteMode.AUTO, authorized=False
    )
    assert repository.write(request) == item


def test_unapproved_system_caller_is_rejected(repository):
    item = commitment(provenance=MemoryProvenance("arbitrary_system", "workflow:1"))
    with pytest.raises(MemoryWriteRejectedError, match="UNAPPROVED_SYSTEM_SOURCE"):
        repository.write(
            write_request(item, action="bad-system", mode=MemoryWriteMode.AUTO, authorized=False)
        )


def test_approved_learned_pattern_can_auto_store(repository):
    item = inferred_pattern()
    assert repository.write(
        write_request(item, action="pattern-1", mode=MemoryWriteMode.AUTO, authorized=False)
    ) == item


def test_unapproved_learned_pattern_source_is_rejected(repository):
    item = inferred_pattern(
        provenance=MemoryProvenance(
            "unknown_rule", "run:1", ("a", "b"), "unknown-v1"
        )
    )
    with pytest.raises(MemoryWriteRejectedError, match="UNAPPROVED_INFERENCE_SOURCE"):
        repository.write(
            write_request(item, action="bad-pattern", mode=MemoryWriteMode.AUTO, authorized=False)
        )


def test_ephemeral_request_is_rejected(repository):
    with pytest.raises(MemoryWriteRejectedError, match="EPHEMERAL_CONTEXT_FORBIDDEN"):
        repository.write(
            write_request(
                explicit_item(), mode=MemoryWriteMode.EPHEMERAL, authorized=True
            )
        )


def test_policy_result_is_typed_and_source_mismatch_is_rejected():
    item = explicit_item()
    request = MemoryWriteRequest(
        item,
        MemoryWriteMode.EXPLICIT,
        SourceIdentity("operator", "action"),
        NOW,
        True,
    )
    result = DeterministicMemoryWritePolicy().evaluate(request)
    assert result.decision is MemoryWriteDecision.REJECT


def test_action_identity_is_hashed_and_does_not_persist_raw_external_id(
    repository, database_path
):
    item = explicit_item()
    request = write_request(item, action="potentially-sensitive-action-text")
    repository.write(request)
    assert request.action_identity.startswith("action:sha256:")
    connection = duckdb.connect(str(database_path))
    stored = connection.execute(
        "SELECT action_identity FROM athlete_context_memory_actions"
    ).fetchone()[0]
    connection.close()
    assert stored == request.action_identity
    assert "potentially-sensitive-action-text" not in stored
