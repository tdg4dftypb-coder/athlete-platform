from datetime import datetime, timedelta, timezone
import json

import pytest

from application.athlete_context_memory import (
    AthleteContextMemoryReadError,
    AthleteContextMemoryService,
    CoachMemoryContextQuery,
    CoachMemoryContextSerializer,
    build_athlete_context_memory_service,
)
from athlete.context_memory import (
    CoachMemoryLimitation,
    CoachMemoryContextBuilder,
    DuckDbContextMemoryRepository,
    MemoryDomain,
    MemoryItem,
    MemoryKind,
    MemoryOrigin,
    MemoryProvenance,
    MemoryRetrievalResult,
    MemorySensitivity,
    MemoryValue,
    MemoryWriteMode,
    MemoryWriteRequest,
)
from training.ingestion.source_identity import SourceIdentity


NOW = datetime(2026, 8, 17, 12, tzinfo=timezone.utc)


def item(
    value: str,
    *,
    subject_id: str = "athlete:primary",
    kind: MemoryKind = MemoryKind.PREFERENCE,
    sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
    valid_from: datetime = NOW - timedelta(days=1),
    valid_until: datetime | None = None,
) -> MemoryItem:
    return MemoryItem.create(
        subject_id=subject_id,
        kind=kind,
        domain=MemoryDomain.TRAINING,
        payload=MemoryValue(f"{kind.value.lower()}_value", value),
        origin=MemoryOrigin.EXPLICIT,
        sensitivity=sensitivity,
        provenance=MemoryProvenance("user", f"input:{value}"),
        confidence=None,
        recorded_at=NOW - timedelta(hours=1),
        valid_from=valid_from,
        valid_until=valid_until,
    )


def persist(repository, memory: MemoryItem) -> MemoryItem:
    return repository.write(
        MemoryWriteRequest(
            item=memory,
            mode=MemoryWriteMode.EXPLICIT,
            source_identity=SourceIdentity("user", memory.memory_id),
            requested_at=NOW,
            explicit_authorized=True,
        )
    )


@pytest.fixture
def repository(tmp_path):
    path = tmp_path / "application-memory.duckdb"
    assert "data/database" not in str(path)
    return DuckDbContextMemoryRepository(path)


@pytest.fixture
def service(repository):
    return build_athlete_context_memory_service(repository)


def query(**changes):
    values = {"subject_id": "athlete:primary", "as_of": NOW}
    values.update(changes)
    return CoachMemoryContextQuery(**values)


def test_empty_repository_returns_valid_empty_context(service):
    context = service.get_coach_memory_context(query())
    assert context.source_memory_ids == ()
    assert context.limitations == (CoachMemoryLimitation.NO_ACTIVE_MEMORY,)


def test_active_memory_is_returned_and_snapshot_identity_is_preserved(repository, service):
    saved = persist(repository, item("early rides"))
    context = service.get_coach_memory_context(query())
    assert context.subject_id == "athlete:primary"
    assert context.as_of == NOW
    assert context.source_memory_ids == (saved.memory_id,)
    assert context.active_preferences[0].value.value == "early rides"


def test_foreign_expired_and_future_memories_are_excluded(repository, service):
    persist(repository, item("foreign", subject_id="athlete:foreign"))
    persist(repository, item("future", valid_from=NOW + timedelta(seconds=1)))
    persist(
        repository,
        item("expired", valid_from=NOW - timedelta(days=2), valid_until=NOW),
    )
    assert service.get_coach_memory_context(query()).source_memory_ids == ()


def test_sensitive_is_excluded_by_default_with_limitation(repository, service):
    persist(repository, item("private", sensitivity=MemorySensitivity.SENSITIVE))
    context = service.get_coach_memory_context(query())
    assert context.source_memory_ids == ()
    assert CoachMemoryLimitation.SENSITIVE_MEMORY_EXCLUDED in context.limitations


def test_sensitive_requires_explicit_query_and_then_keeps_safe_provenance(repository, service):
    saved = persist(repository, item("private", sensitivity=MemorySensitivity.SENSITIVE))
    context = service.get_coach_memory_context(query(include_sensitive=True))
    projection = context.active_preferences[0]
    assert projection.memory_id == saved.memory_id
    assert projection.source_ref == "input:private"


def test_query_has_safe_sensitive_default_and_canonicalizes_filters():
    value = query(
        domains=(MemoryDomain.TRAINING, MemoryDomain.HEALTH),
        kinds=(MemoryKind.GOAL, MemoryKind.CONSTRAINT),
    )
    assert value.include_sensitive is False
    assert value.domains == (MemoryDomain.HEALTH, MemoryDomain.TRAINING)
    assert value.kinds == (MemoryKind.CONSTRAINT, MemoryKind.GOAL)
    assert not hasattr(value, "limit")


def test_application_service_preserves_builder_fingerprint(repository, service):
    persist(repository, item("morning"))
    first = service.get_coach_memory_context(query())
    second = service.get_coach_memory_context(query())
    assert first == second
    assert first.fingerprint == second.fingerprint


def test_semantic_change_changes_fingerprint(repository, service):
    first = service.get_coach_memory_context(query())
    persist(repository, item("morning"))
    second = service.get_coach_memory_context(query())
    assert first.fingerprint != second.fingerprint


def test_category_and_global_bounds_cannot_be_overridden(repository, service):
    for index in range(12):
        persist(repository, item(f"preference-{index}"))
    context = service.get_coach_memory_context(query())
    assert len(context.active_preferences) == 8
    assert len(context.source_memory_ids) <= 32
    assert CoachMemoryLimitation.MEMORY_CONTEXT_TRUNCATED in context.limitations


def test_serializer_is_deterministic_typed_and_utc(repository, service):
    persist(repository, item("morning"))
    context = service.get_coach_memory_context(query())
    serializer = CoachMemoryContextSerializer()
    first = serializer.serialize(context)
    second = serializer.serialize(context)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["contract_version"] == "1.0"
    assert first["as_of"] == "2026-08-17T12:00:00+00:00"
    projected = first["active_preferences"][0]
    assert projected["kind"] == "PREFERENCE"
    assert projected["domain"] == "TRAINING"
    assert projected["origin"] == "EXPLICIT"
    assert first["fingerprint"] == context.fingerprint
    assert first["source_memory_ids"] == list(context.source_memory_ids)


def test_serializer_preserves_limitations_and_contains_no_persistence_internals(service):
    payload = CoachMemoryContextSerializer().serialize(
        service.get_coach_memory_context(query())
    )
    assert payload["limitations"] == ["NO_ACTIVE_MEMORY"]
    text = json.dumps(payload, sort_keys=True)
    for forbidden in ("semantic_json", "record_json", "action_identity", "tombstone"):
        assert forbidden not in text


def test_serializer_cannot_leak_unauthorized_sensitive_source_ref(repository, service):
    persist(repository, item("private", sensitivity=MemorySensitivity.SENSITIVE))
    payload = CoachMemoryContextSerializer().serialize(
        service.get_coach_memory_context(query())
    )
    assert "input:private" not in json.dumps(payload, sort_keys=True)


class FailingBuilder:
    def build(self, request):
        raise OSError("duckdb path and internal details")


def test_repository_failure_maps_to_typed_application_error_without_leaking_details():
    service = AthleteContextMemoryService(FailingBuilder())
    with pytest.raises(AthleteContextMemoryReadError) as captured:
        service.get_coach_memory_context(query())
    assert str(captured.value) == "durable athlete memory could not be read"
    assert "duckdb" not in str(captured.value).lower()


def test_service_exposes_no_write_or_history_browser_methods(service):
    for method in ("remember", "forget", "revoke", "supersede", "write", "list_all"):
        assert not hasattr(service, method)


def test_service_depends_on_builder_protocol_without_opening_a_database():
    class EmptyReadPort:
        def retrieve(self, request):
            return MemoryRetrievalResult((), False, False)

    class RecordingBuilder:
        def __init__(self):
            self.request = None

        def build(self, request):
            self.request = request
            return CoachMemoryContextBuilder(EmptyReadPort()).build(request)

    builder = RecordingBuilder()
    result = AthleteContextMemoryService(builder).get_coach_memory_context(query())
    assert result.source_memory_ids == ()
    assert builder.request.subject_id == "athlete:primary"
