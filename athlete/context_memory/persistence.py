"""DuckDB persistence and controlled lifecycle operations for Context Memory."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading

import duckdb

from athlete.context_memory.errors import (
    ExplicitAuthorizationRequiredError,
    ForgottenMemoryReplayError,
    IllegalMemoryLifecycleTransitionError,
    MemoryCollisionError,
    MemoryNotFoundError,
    MemoryPersistenceInvariantError,
    MemoryWriteRejectedError,
)
from athlete.context_memory.models import (
    ForgottenMemoryTombstone,
    MemoryItem,
    MemoryKind,
    MemoryStatus,
)
from athlete.context_memory.policy import (
    DeterministicMemoryWritePolicy,
    MemoryLifecycleRequest,
    MemoryWriteDecision,
    MemoryWriteRequest,
)
from athlete.context_memory.serialization import MemoryItemCodec
from athlete.context_memory.retrieval import (
    MAX_RETRIEVAL_ITEMS,
    MemoryRetrievalRequest,
    MemoryRetrievalResult,
)
from athlete.context_memory.models import MemoryDomain


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class AthleteContextMemorySchema:
    """Idempotent schema setup; deliberately does not alter athlete_memory_events."""

    @staticmethod
    def create(connection: duckdb.DuckDBPyConnection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_context_memory_items (
                memory_id VARCHAR PRIMARY KEY,
                subject_id VARCHAR NOT NULL,
                kind VARCHAR NOT NULL,
                domain VARCHAR NOT NULL,
                payload_json VARCHAR NOT NULL,
                origin VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                sensitivity VARCHAR NOT NULL,
                source_type VARCHAR NOT NULL,
                source_ref VARCHAR,
                evidence_refs_json VARCHAR NOT NULL,
                confidence VARCHAR,
                inference_rule_version VARCHAR,
                recorded_at TIMESTAMP NOT NULL,
                observed_at TIMESTAMP,
                valid_from TIMESTAMP NOT NULL,
                valid_until TIMESTAMP,
                supersedes_memory_id VARCHAR,
                lifecycle_at TIMESTAMP,
                record_schema_version VARCHAR NOT NULL,
                semantic_json VARCHAR NOT NULL,
                record_json VARCHAR NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_context_memory_tombstones (
                memory_id VARCHAR PRIMARY KEY,
                subject_id VARCHAR NOT NULL,
                forgotten_at TIMESTAMP NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_context_memory_actions (
                action_identity VARCHAR PRIMARY KEY,
                memory_id VARCHAR NOT NULL,
                action_type VARCHAR NOT NULL,
                requested_at TIMESTAMP NOT NULL
            )
            """
        )


class DuckDbContextMemoryRepository:
    """Policy-gated repository; no generic update or retrieval/ranking API."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        policy: DeterministicMemoryWritePolicy | None = None,
        codec: MemoryItemCodec | None = None,
        initialize_schema: bool = True,
    ) -> None:
        self._db_path = str(db_path)
        self._policy = policy or DeterministicMemoryWritePolicy()
        self._codec = codec or MemoryItemCodec()
        self._lock = threading.Lock()
        if not isinstance(initialize_schema, bool):
            raise TypeError("initialize_schema must be bool")
        if initialize_schema:
            self.initialize_schema()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self._db_path)

    def initialize_schema(self) -> None:
        with self._lock:
            if self._db_path != ":memory:":
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            connection = self._connect()
            try:
                AthleteContextMemorySchema.create(connection)
            finally:
                connection.close()

    def write(self, request: MemoryWriteRequest) -> MemoryItem:
        if not isinstance(request, MemoryWriteRequest):
            raise TypeError("request must be MemoryWriteRequest")
        result = self._policy.evaluate(request)
        if result.decision is MemoryWriteDecision.REQUIRE_EXPLICIT_AUTHORIZATION:
            raise ExplicitAuthorizationRequiredError(result.reason.value)
        if result.decision is MemoryWriteDecision.REJECT:
            raise MemoryWriteRejectedError(result.reason.value)

        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN TRANSACTION")
                if self._tombstone_row(connection, request.item.memory_id) is not None:
                    raise ForgottenMemoryReplayError(request.item.memory_id)

                existing = self._item_row(connection, request.item.memory_id)
                if existing is not None:
                    self._verify_same_semantics(existing, request.item)
                    item = self._decode_row(existing)
                    self._claim_action(
                        connection,
                        request.action_identity,
                        request.item.memory_id,
                        "WRITE",
                        request.requested_at,
                    )
                    connection.execute("COMMIT")
                    return item

                self._claim_action(
                    connection,
                    request.action_identity,
                    request.item.memory_id,
                    "WRITE",
                    request.requested_at,
                )
                if request.item.supersedes_memory_id is None:
                    self._insert_item(connection, request.item)
                else:
                    self._atomic_supersede(connection, request.item, request.requested_at)
                connection.execute("COMMIT")
                return request.item
            except Exception:
                self._rollback(connection)
                raise
            finally:
                connection.close()

    def get_by_id(self, memory_id: str) -> MemoryItem | None:
        with self._lock:
            connection = self._connect()
            try:
                row = self._item_row(connection, memory_id)
                return None if row is None else self._decode_row(row)
            finally:
                connection.close()

    def exists(self, memory_id: str) -> bool:
        return self.get_by_id(memory_id) is not None

    def get_tombstone(self, memory_id: str) -> ForgottenMemoryTombstone | None:
        with self._lock:
            connection = self._connect()
            try:
                row = self._tombstone_row(connection, memory_id)
                if row is None:
                    return None
                return ForgottenMemoryTombstone(row[0], row[1], _aware_utc(row[2]))
            finally:
                connection.close()

    def retrieve(self, request: MemoryRetrievalRequest) -> MemoryRetrievalResult:
        if not isinstance(request, MemoryRetrievalRequest):
            raise TypeError("request must be MemoryRetrievalRequest")
        where, parameters = self._active_where(request)
        origin_order = (
            "CASE origin WHEN 'EXPLICIT' THEN 0 WHEN 'SYSTEM' THEN 1 ELSE 2 END"
        )
        confidence_order = (
            "CASE WHEN origin = 'INFERRED' THEN "
            "CASE confidence WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END "
            "ELSE 0 END"
        )
        query = f"""
            SELECT record_json, semantic_json
            FROM athlete_context_memory_items
            WHERE {where}
            ORDER BY {origin_order}, {confidence_order},
                     valid_from DESC, recorded_at DESC, memory_id ASC
            LIMIT ?
        """
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    query, [*parameters, request.limit + 1]
                ).fetchall()
                sensitive_excluded = False
                if not request.include_sensitive:
                    sensitive_where, sensitive_parameters = self._active_where(
                        request, sensitivity_override="SENSITIVE"
                    )
                    sensitive_excluded = connection.execute(
                        f"SELECT 1 FROM athlete_context_memory_items WHERE {sensitive_where} LIMIT 1",
                        sensitive_parameters,
                    ).fetchone() is not None
                return MemoryRetrievalResult(
                    items=tuple(self._decode_row(row) for row in rows[: request.limit]),
                    truncated=len(rows) > request.limit,
                    sensitive_excluded=sensitive_excluded,
                )
            finally:
                connection.close()

    def list_active(
        self, subject_id: str, as_of: datetime, *, limit: int = MAX_RETRIEVAL_ITEMS,
        include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.retrieve(MemoryRetrievalRequest(
            subject_id, as_of, limit=limit, include_sensitive=include_sensitive
        )).items

    def list_active_by_kind(
        self, subject_id: str, as_of: datetime, kind: MemoryKind, *,
        limit: int = MAX_RETRIEVAL_ITEMS, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.retrieve(MemoryRetrievalRequest(
            subject_id, as_of, kinds=(kind,), limit=limit,
            include_sensitive=include_sensitive,
        )).items

    def list_active_by_domain(
        self, subject_id: str, as_of: datetime, domain: MemoryDomain, *,
        limit: int = MAX_RETRIEVAL_ITEMS, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.retrieve(MemoryRetrievalRequest(
            subject_id, as_of, domains=(domain,), limit=limit,
            include_sensitive=include_sensitive,
        )).items

    def list_active_by_kind_and_domain(
        self, subject_id: str, as_of: datetime, kind: MemoryKind,
        domain: MemoryDomain, *, limit: int = MAX_RETRIEVAL_ITEMS,
        include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.retrieve(MemoryRetrievalRequest(
            subject_id, as_of, kinds=(kind,), domains=(domain,), limit=limit,
            include_sensitive=include_sensitive,
        )).items

    def list_recent_corrections(self, subject_id: str, as_of: datetime, *,
        limit: int = 4, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.list_active_by_kind(
            subject_id, as_of, MemoryKind.CORRECTION,
            limit=limit, include_sensitive=include_sensitive,
        )

    def list_active_commitments(self, subject_id: str, as_of: datetime, *,
        limit: int = 6, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.list_active_by_kind(
            subject_id, as_of, MemoryKind.COMMITMENT,
            limit=limit, include_sensitive=include_sensitive,
        )

    def list_active_goals(self, subject_id: str, as_of: datetime, *,
        limit: int = 4, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.list_active_by_kind(
            subject_id, as_of, MemoryKind.GOAL,
            limit=limit, include_sensitive=include_sensitive,
        )

    def list_active_constraints(self, subject_id: str, as_of: datetime, *,
        limit: int = 8, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.list_active_by_kind(
            subject_id, as_of, MemoryKind.CONSTRAINT,
            limit=limit, include_sensitive=include_sensitive,
        )

    def list_active_preferences(self, subject_id: str, as_of: datetime, *,
        limit: int = 8, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.list_active_by_kind(
            subject_id, as_of, MemoryKind.PREFERENCE,
            limit=limit, include_sensitive=include_sensitive,
        )

    def list_active_learned_patterns(self, subject_id: str, as_of: datetime, *,
        limit: int = 4, include_sensitive: bool = False,
    ) -> tuple[MemoryItem, ...]:
        return self.list_active_by_kind(
            subject_id, as_of, MemoryKind.LEARNED_PATTERN,
            limit=limit, include_sensitive=include_sensitive,
        )

    def revoke(self, request: MemoryLifecycleRequest) -> MemoryItem:
        self._require_lifecycle_authorization(request)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN TRANSACTION")
                row = self._item_row(connection, request.memory_id)
                if row is None:
                    if self._tombstone_row(connection, request.memory_id) is not None:
                        raise IllegalMemoryLifecycleTransitionError("cannot revoke forgotten memory")
                    raise MemoryNotFoundError(request.memory_id)
                item = self._decode_row(row)
                if item.status is MemoryStatus.REVOKED:
                    self._claim_action(
                        connection, request.action_identity, request.memory_id,
                        "REVOKE", request.requested_at,
                    )
                    connection.execute("COMMIT")
                    return item
                if item.status is not MemoryStatus.ACTIVE:
                    raise IllegalMemoryLifecycleTransitionError(
                        f"cannot revoke {item.status.value} memory"
                    )
                revoked = item.transition_to(MemoryStatus.REVOKED)
                self._claim_action(
                    connection, request.action_identity, request.memory_id,
                    "REVOKE", request.requested_at,
                )
                self._update_lifecycle(connection, revoked, request.requested_at)
                connection.execute("COMMIT")
                return revoked
            except Exception:
                self._rollback(connection)
                raise
            finally:
                connection.close()

    def forget(self, request: MemoryLifecycleRequest) -> ForgottenMemoryTombstone:
        self._require_lifecycle_authorization(request)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN TRANSACTION")
                existing_tombstone = self._tombstone_row(connection, request.memory_id)
                if existing_tombstone is not None:
                    self._claim_action(
                        connection, request.action_identity, request.memory_id,
                        "FORGET", request.requested_at,
                    )
                    connection.execute("COMMIT")
                    return ForgottenMemoryTombstone(
                        existing_tombstone[0], existing_tombstone[1],
                        _aware_utc(existing_tombstone[2]),
                    )
                row = self._item_row(connection, request.memory_id)
                if row is None:
                    raise MemoryNotFoundError(request.memory_id)
                item = self._decode_row(row)
                self._claim_action(
                    connection, request.action_identity, request.memory_id,
                    "FORGET", request.requested_at,
                )
                connection.execute(
                    "INSERT INTO athlete_context_memory_tombstones VALUES (?, ?, ?)",
                    [item.memory_id, item.subject_id, _naive_utc(request.requested_at)],
                )
                self._delete_item_in_transaction(connection, item.memory_id)
                connection.execute("COMMIT")
                return ForgottenMemoryTombstone(
                    item.memory_id, item.subject_id, request.requested_at
                )
            except Exception:
                self._rollback(connection)
                raise
            finally:
                connection.close()

    @staticmethod
    def _require_lifecycle_authorization(request: MemoryLifecycleRequest) -> None:
        if not isinstance(request, MemoryLifecycleRequest):
            raise TypeError("request must be MemoryLifecycleRequest")
        if not request.explicit_authorized:
            raise ExplicitAuthorizationRequiredError(
                "lifecycle operation requires explicit authorization"
            )

    def _atomic_supersede(
        self,
        connection: duckdb.DuckDBPyConnection,
        new_item: MemoryItem,
        at: datetime,
    ) -> None:
        old_row = self._item_row(connection, new_item.supersedes_memory_id)
        if old_row is None:
            raise MemoryNotFoundError(new_item.supersedes_memory_id)
        old_item = self._decode_row(old_row)
        if old_item.status is not MemoryStatus.ACTIVE:
            raise IllegalMemoryLifecycleTransitionError(
                f"superseded memory must be ACTIVE, got {old_item.status.value}"
            )
        if old_item.subject_id != new_item.subject_id:
            raise MemoryCollisionError("supersession subject mismatch")
        compatible_kind = (
            new_item.kind is MemoryKind.CORRECTION or old_item.kind is new_item.kind
        )
        if not compatible_kind or old_item.domain is not new_item.domain:
            raise MemoryCollisionError("supersession kind/domain mismatch")
        if new_item.status is not MemoryStatus.ACTIVE:
            raise IllegalMemoryLifecycleTransitionError("new superseding memory must be ACTIVE")
        self._insert_item(connection, new_item)
        self._update_lifecycle(
            connection, old_item.transition_to(MemoryStatus.SUPERSEDED), at
        )

    def _insert_item(
        self, connection: duckdb.DuckDBPyConnection, item: MemoryItem
    ) -> None:
        provenance = item.provenance
        connection.execute(
            """
            INSERT INTO athlete_context_memory_items VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                NULL, ?, ?, ?
            )
            """,
            [
                item.memory_id,
                item.subject_id,
                item.kind.value,
                item.domain.value,
                item.payload.canonical_json(),
                item.origin.value,
                item.status.value,
                item.sensitivity.value,
                provenance.source_type,
                provenance.source_ref,
                self._json_list(provenance.evidence_refs),
                None if item.confidence is None else item.confidence.value,
                provenance.inference_rule_version,
                _naive_utc(item.recorded_at),
                None if item.observed_at is None else _naive_utc(item.observed_at),
                _naive_utc(item.valid_from),
                None if item.valid_until is None else _naive_utc(item.valid_until),
                item.supersedes_memory_id,
                self._codec.SCHEMA_VERSION,
                self._codec.encode_semantics(item),
                self._codec.encode(item),
            ],
        )

    def _update_lifecycle(
        self,
        connection: duckdb.DuckDBPyConnection,
        item: MemoryItem,
        at: datetime,
    ) -> None:
        connection.execute(
            """
            UPDATE athlete_context_memory_items
            SET status = ?, lifecycle_at = ?, record_json = ?
            WHERE memory_id = ? AND status = 'ACTIVE'
            """,
            [item.status.value, _naive_utc(at), self._codec.encode(item), item.memory_id],
        )
        persisted = connection.execute(
            "SELECT status, record_json FROM athlete_context_memory_items WHERE memory_id = ?",
            [item.memory_id],
        ).fetchone()
        if persisted != (item.status.value, self._codec.encode(item)):
            raise MemoryPersistenceInvariantError("lifecycle compare-and-set failed")

    @staticmethod
    def _delete_item_in_transaction(
        connection: duckdb.DuckDBPyConnection, memory_id: str
    ) -> None:
        connection.execute(
            "DELETE FROM athlete_context_memory_items WHERE memory_id = ?",
            [memory_id],
        )

    def _verify_same_semantics(self, row, incoming: MemoryItem) -> None:
        if row[1] != self._codec.encode_semantics(incoming):
            raise MemoryCollisionError(
                f"memory_id {incoming.memory_id} has different semantic content"
            )

    @staticmethod
    def _active_where(
        request: MemoryRetrievalRequest,
        *,
        sensitivity_override: str | None = None,
    ) -> tuple[str, list]:
        clauses = [
            "subject_id = ?",
            "status = 'ACTIVE'",
            "valid_from <= ?",
            "(valid_until IS NULL OR ? < valid_until)",
        ]
        as_of = _naive_utc(request.as_of)
        parameters: list = [request.subject_id, as_of, as_of]
        if request.kinds:
            clauses.append("kind IN (" + ",".join("?" for _ in request.kinds) + ")")
            parameters.extend(item.value for item in request.kinds)
        if request.domains:
            clauses.append("domain IN (" + ",".join("?" for _ in request.domains) + ")")
            parameters.extend(item.value for item in request.domains)
        if sensitivity_override is not None:
            clauses.append("sensitivity = ?")
            parameters.append(sensitivity_override)
        elif not request.include_sensitive:
            clauses.append("sensitivity = 'NORMAL'")
        return " AND ".join(clauses), parameters

    def _decode_row(self, row) -> MemoryItem:
        try:
            item = self._codec.decode(row[0])
        except Exception as error:
            raise MemoryPersistenceInvariantError("invalid persisted memory item") from error
        if self._codec.encode_semantics(item) != row[1]:
            raise MemoryPersistenceInvariantError("persisted semantic payload mismatch")
        return item

    @staticmethod
    def _item_row(connection, memory_id):
        return connection.execute(
            """
            SELECT record_json, semantic_json
            FROM athlete_context_memory_items WHERE memory_id = ?
            """,
            [memory_id],
        ).fetchone()

    @staticmethod
    def _tombstone_row(connection, memory_id):
        return connection.execute(
            """
            SELECT memory_id, subject_id, forgotten_at
            FROM athlete_context_memory_tombstones WHERE memory_id = ?
            """,
            [memory_id],
        ).fetchone()

    @staticmethod
    def _claim_action(connection, identity, memory_id, action_type, requested_at):
        existing = connection.execute(
            """
            SELECT memory_id, action_type FROM athlete_context_memory_actions
            WHERE action_identity = ?
            """,
            [identity],
        ).fetchone()
        if existing is not None:
            if existing != (memory_id, action_type):
                raise MemoryCollisionError("source action identity collision")
            return
        connection.execute(
            "INSERT INTO athlete_context_memory_actions VALUES (?, ?, ?, ?)",
            [identity, memory_id, action_type, _naive_utc(requested_at)],
        )

    @staticmethod
    def _json_list(values: tuple[str, ...]) -> str:
        import json
        return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _rollback(connection) -> None:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
