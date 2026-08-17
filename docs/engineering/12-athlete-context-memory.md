# Athlete Context & Memory v2

## Status

Stage 31 — Athlete Context & Memory v2 is **CLOSED / 100%**. Stage 31.2 freezes
the pure domain contract, Stage 31.3 adds isolated DuckDB persistence and a
deterministic write policy, Stage 31.4 adds bounded typed retrieval and
durable-memory-only Coach context assembly, Stage 31.5 adds the read-only
application contract, and Stage 31.6 certifies explicit production composition
without activating it against the production database. Roadmap V2 progress is
**55%**.

## Purpose and boundary

Athlete Context Memory stores small, durable pieces of athlete context that
cannot be reconstructed from current canonical operational state. It evolves
the platform without replacing the existing `athlete/memory/` activity-event
history:

- `ACTIVITY_RECORDED` and `WORKOUT_COMPLETED` remain unchanged;
- Health, Biomarkers, Training Plan, Decision, Adaptation, Reconciliation, and
  Production Runtime remain the owners of their live state;
- context memory is not a cache and does not store conversation transcripts.

The separate `athlete/context_memory/` boundary makes that distinction explicit.

## Frozen taxonomy

Kinds:

- `PREFERENCE`
- `CONSTRAINT`
- `GOAL`
- `CORRECTION`
- `COMMITMENT`
- `LEARNED_PATTERN`

Domains:

- `TRAINING`
- `RECOVERY`
- `HEALTH`
- `LIFESTYLE`
- `EQUIPMENT`
- `NUTRITION`

Origins:

- `EXPLICIT` — supplied by a user or operator;
- `INFERRED` — produced by a deterministic, versioned rule from referenced
  evidence;
- `SYSTEM` — system-originated context such as a durable Coach commitment.

`INFERRED` always requires `LOW`, `MEDIUM`, or `HIGH` confidence, an inference
rule version, and evidence. Confidence and inference rule versions are forbidden
for other origins. `LEARNED_PATTERN` additionally requires at least two evidence
references. A `CORRECTION` is explicit and references the memory it corrects; a
`COMMITMENT` is system-originated.

Sensitivity is an independent `NORMAL` or `SENSITIVE` classification. It does
not itself change origin or lifecycle.

## Identity and subject

The current single-athlete deployment uses the explicit subject identity:

```text
athlete:primary
```

Memory identity is `memory:sha256:<digest>` over canonical semantic data. The
digest includes subject, taxonomy, bounded payload, provenance, confidence,
validity, observation time, sensitivity, and supersession. Attribute and
evidence order are canonicalized. It excludes `recorded_at` and lifecycle
status, so an idempotent retry keeps the same identity and a lifecycle change
does not create a different fact.

## Payload and provenance

`MemoryValue` is not arbitrary JSON. It contains:

- one canonical key;
- one bounded scalar value (`string`, `bool`, `int`, or finite `float`);
- at most eight uniquely keyed bounded scalar attributes.

The main text value is limited to 512 characters, attribute text to 256, and
the canonical payload to 2048 UTF-8 bytes. Transcript-shaped keys are rejected.

`MemoryProvenance` contains references, not raw evidence:

- canonical `source_type`;
- optional bounded `source_ref`;
- zero to sixteen unique, canonically sorted `evidence_refs`;
- optional `inference_rule_version`, used only by inferred memory.

Large evidence sets must be represented by a canonical aggregate artifact and
referenced by ID.

## Lifecycle

Statuses are:

- `ACTIVE`
- `SUPERSEDED`
- `REVOKED`
- `FORGOTTEN`

The only runtime transitions allowed by the domain helper are:

```text
ACTIVE -> SUPERSEDED
ACTIVE -> REVOKED
ACTIVE -> FORGOTTEN
```

Terminal items cannot be reactivated. A new item may reference exactly one
prior ID through `supersedes_memory_id`; constructing it does not mutate the
prior item. Compatibility of the two items and atomic persistence are Stage
31.3 responsibilities.

`REVOKED` preserves historical payload. `FORGOTTEN` represents the request for
persistence-level redaction. `ForgottenMemoryTombstone` deliberately retains
only memory ID, subject ID, and forget time; it cannot retain original payload
or evidence.

## Persistence architecture

Context Memory uses separate tables and never writes durable context items to
the existing `athlete_memory_events` activity history:

```text
athlete_context_memory_items
athlete_context_memory_tombstones
athlete_context_memory_actions
```

`athlete_context_memory_items` preserves every field required to hydrate a
validated `MemoryItem`. Payload, evidence references, provenance, enum values,
and timestamps use canonical JSON or explicit columns; Python `repr` is never
persisted. `MemoryItemCodec` provides a deterministic full round trip and a
separate canonical semantic representation used for collision detection.

The canonical production location follows the existing Athlete Memory
architecture: the Health database resolved by `HEALTH_DB_PATH`, defaulting to
`data/database/health.duckdb`. Context Memory uses only its own tables inside
that database. The path helper has no I/O, and Stage 31.3 does not wire or run a
production repository.

Schema creation is additive and idempotent. Stage 31.3 tests it only against
isolated DuckDB files; no production migration or data seeding is performed.

## Idempotency and collision behavior

Writing an already persisted `memory_id` with identical canonical semantics is
an idempotent success and returns the existing record. Differences in
`recorded_at` do not create a second semantic item. The same ID with different
semantic content raises a typed collision and is never overwritten or merged.

Every write or lifecycle request carries an existing `SourceIdentity`. Its
provider must agree with `MemoryProvenance.source_type`. The provider/external
identity is hashed into `action:sha256:<digest>` before persistence, providing a
stable replay guard without retaining potentially descriptive external action
text. Reusing one action identity for another item or operation is a collision.

## Deterministic write policy

Public persistence accepts `MemoryWriteRequest`, not an unconstrained
`MemoryItem`. Policy results are typed as:

- `ALLOW`
- `REQUIRE_EXPLICIT_AUTHORIZATION`
- `REJECT`

Explicit authorization is required for preferences, constraints, goals,
corrections, user-provided equipment/lifestyle context, nutrition/health
context, and every sensitive explicit item. `EPHEMERAL` requests are rejected.
There is no conversation parser or implicit authorization inference.

Automatic writes are limited to:

- `SYSTEM` commitments from the approved `coach_commitment_service` source;
- valid, normal-sensitivity `LEARNED_PATTERN` items from the approved
  `approved_memory_inference` source.

Arbitrary system callers and unapproved inference sources are rejected.
Sensitive inferred memory is always rejected in v1, even when a caller supplies
an authorization flag.

## Transactional lifecycle persistence

Supersession executes in one explicit transaction:

1. verify the previous item exists and remains `ACTIVE`;
2. verify subject and domain compatibility;
3. require the same kind, except that an explicit `CORRECTION` may supersede a
   different kind in the same domain;
4. insert the new `ACTIVE` item;
5. compare-and-set the prior item to `SUPERSEDED`;
6. commit, or roll back every action and row change.

There is no generic update API. Lifecycle changes preserve deterministic
`memory_id` and update only controlled status/audit representation.

`revoke` requires an explicitly authorized lifecycle request. It transitions
only `ACTIVE -> REVOKED`; a repeated revoke is idempotent, while superseded or
forgotten memory cannot be revoked.

## Forget, redaction, and replay protection

`forget` is an explicitly authorized transaction:

1. verify the item or an existing tombstone;
2. insert a minimal tombstone;
3. delete the complete item row containing payload, source reference, evidence,
   and inference details;
4. commit atomically.

After success, `get_by_id` cannot expose the original item. The tombstone keeps
only `memory_id`, `subject_id`, and `forgotten_at`. A separate action table
contains only hashed action identity, memory ID, operation type, and time. The
tombstone blocks automatic retry/replay of the same semantic ID. A genuinely
new explicit user action must produce a new semantic item and therefore a new
ID.

This is application-level hard forget/redaction. DuckDB files, filesystem
snapshots, backups, WAL behavior, and storage media may retain historical bytes;
Stage 31.3 does not claim physical shredding, vacuum, or backup erasure.

## Deterministic retrieval

Every active retrieval requires an explicit `subject_id` and timezone-aware UTC
`as_of`. Active rows satisfy the frozen half-open rule:

```text
status = ACTIVE
AND valid_from <= as_of
AND (valid_until IS NULL OR as_of < valid_until)
```

Future, expired, superseded, revoked, and forgotten items are excluded in SQL.
Queries can filter by bounded tuples of kind and domain; filtered values and
subject IDs are always parameters. There is no unbounded public `list_all`.
The hard public result limit is 32 items, and SQL fetches at most `limit + 1`
only to report deterministic truncation.

The repository provides typed convenience reads for active preferences,
constraints, goals, commitments, learned patterns, and recent corrections.
Every convenience path still requires subject and `as_of` and retains a hard
limit.

### Ordering and relevance

No relevance float, NLP classifier, embedding, or vector search is used. SQL
orders selected rows lexicographically:

1. requested kind/domain are exact filters;
2. `EXPLICIT`, then `SYSTEM`, then `INFERRED`;
3. among inferred items only: `HIGH`, `MEDIUM`, then `LOW` confidence;
4. `valid_from` descending;
5. `recorded_at` descending;
6. `memory_id` ascending as the stable tie-breaker.

Confidence can therefore order learned patterns within their trust tier but
cannot outrank an explicit preference or constraint.

### Sensitive retrieval

Normal requests return `NORMAL` memory only. An explicit
`include_sensitive=True` policy input is required to retrieve `SENSITIVE`
items. When sensitive rows match a normal request, the result reports that they
were excluded. Coach-facing projection additionally suppresses a sensitive
`source_ref` unless the projection is constructed with sensitive authorization.
No auth subsystem is implied by this flag.

## CoachMemoryContext

`CoachMemoryContext` is deliberately not the future full Coach context. It is
an immutable snapshot of durable Context Memory for one subject and `as_of`.
It never reads or embeds current plan, recovery, biomarkers, Decision,
Production Runtime, Apple Health, Intervals.icu, or activity-event history.

The builder produces bounded `CoachMemoryItem` projections containing only:

- memory ID and typed kind/domain;
- bounded `MemoryValue`;
- origin and optional confidence;
- validity start and sensitivity;
- safe provenance references and inference rule version.

It does not expose semantic/record JSON, action hashes, table fields, or
tombstone internals.

Per-category limits are:

| Category | Maximum |
|---|---:|
| active preferences | 8 |
| active constraints | 8 |
| active goals | 4 |
| active commitments | 6 |
| relevant learned patterns | 4 |
| recent corrections | 4 |

The global maximum is 32 source items. If global truncation is needed, items
are retained in this frozen priority:

```text
constraints
goals
corrections
commitments
preferences
learned patterns
```

Superseded original values never reappear beside active corrections. If active
replacement-chain corruption is detected, the conflicting selected items are
excluded rather than guessed, and an invariant limitation is emitted.

### Limitations and empty context

Typed limitations are:

- `MEMORY_CONTEXT_TRUNCATED`
- `SENSITIVE_MEMORY_EXCLUDED`
- `INCONSISTENT_ACTIVE_MEMORY`
- `NO_ACTIVE_MEMORY`

An empty result is a valid context with `NO_ACTIVE_MEMORY`, not a failure.
There are no generated natural-language warnings in this layer.

### Snapshot fingerprint

Each context has `coach-memory-context:sha256:<digest>` over canonical subject,
UTC `as_of`, ordered projected semantic content, provenance summary, and typed
limitations. The same database, request, and `as_of` produce the same snapshot
and fingerprint regardless of insertion order. A semantic change or different
snapshot time changes the fingerprint.

## Stage 32-facing application boundary

Stage 31.5 is complete. `AthleteContextMemoryService` is the stable, read-only
application boundary through which a future Stage 32 caller can obtain a
`CoachMemoryContext`. The caller supplies an immutable
`CoachMemoryContextQuery` containing subject, UTC `as_of`, optional typed
domains/kinds, and the explicit sensitive policy. It does not see DuckDB,
repository objects, retrieval limits, codecs, lifecycle storage, or SQL.

The standard query defaults `include_sensitive` to false. It preserves the
builder-owned snapshot identity, fingerprint, limitations, source memory IDs,
category bounds, global bound, ordering, and safe provenance without
reconstructing any of them in the application layer. Empty memory remains a
valid empty context. Persistence failures cross the boundary as the typed
`AthleteContextMemoryReadError`, without persistence details in its public
message.

`CoachMemoryContextSerializer` provides the deterministic versioned read
representation (`contract_version = "1.0"`). Enums use their canonical values,
UTC datetimes use ISO 8601, arrays retain builder order, and fingerprint,
limitations, source IDs, and authorized safe provenance are preserved. It
contains no persistence JSON, tombstones, or action identities.

The service is injected with the context builder (or composed from an injected
read port). Importing the module opens no database, and the service exposes no
remember, forget, revoke, supersede, or other write operation. Production
composition is described below.

This boundary still returns only `CoachMemoryContext`; it is not the future
full `CoachContext`. It does not compose Training Plan, recovery, biomarkers,
Decision Intelligence, Activity Calendar, Production Runtime, Apple Health,
Intervals.icu, Zwift, or any other live source.

## Production composition and initialization

`build_context_memory_read_service(path)` constructs the Stage 32-facing
`AthleteContextMemoryService` with a repository whose automatic schema
initialization is disabled. Construction and module import perform no database
open, directory creation, schema mutation, seed, memory write, learned-pattern
generation, runtime execution, or background work. A read expects a previously
certified schema and maps persistence failure to the typed application error.

Schema creation is a separate operator-controlled action:

```python
initialize_context_memory_schema(path)
```

It creates only `athlete_context_memory_items`,
`athlete_context_memory_tombstones`, and `athlete_context_memory_actions` using
additive `CREATE TABLE IF NOT EXISTS`. It is idempotent and neither alters nor
deletes `athlete_memory_events` or its data. Stage 31.6 certified this behavior
only on isolated DuckDB files. It did **not** invoke initialization on canonical
`data/database/health.duckdb`; any first production initialization remains an
explicit operator gate.

Certification covers read/construction/import write safety, sensitive policy,
hard forget and minimal tombstones, replay protection, atomic supersession and
rollback, idempotent revoke, bounded mixed context, empty context, deterministic
serialization/fingerprint, malformed persistence handling, collision and
lifecycle conflicts, and legacy Activity/Calendar/Reconciliation/Assessment/
Morning Briefing/Production Runtime regressions.

## Temporal semantics

All domain timestamps are supplied by callers and must be timezone-aware UTC.
Constructors never read the system clock.

- `recorded_at`: when the item was recorded;
- `observed_at`: optional time at which inference evidence was observed;
- `valid_from`: inclusive start of validity;
- `valid_until`: optional exclusive end of validity.

Validity is half-open: `[valid_from, valid_until)`. `is_active(as_of)` is true
only for lifecycle status `ACTIVE` inside that interval.

## Final Stage 31 boundaries

Stage 31 is closed, but intentionally does **not** include:

- HTTP endpoint;
- LLM, prompt assembly, conversation storage, conversation extraction,
  embeddings, or vector search;
- Coach memory writes or controlled actions;
- full CoachContext or live operational context assembly;
- automatic learning pipeline or mobile changes;
- HealthKit, Apple Health, Intervals.icu, or Zwift live-source integration;
- Stage 32 prompt assembly or read/write integration beyond this bounded
  durable-memory read contract.

These contracts must not be extended with current recovery, current plan, or
runtime-specific memory types. Such information remains live canonical state.
The next milestone is the mandatory Data Integration Gate for Apple Health /
HealthKit, Intervals.icu, and Zwift; it was not started by Stage 31.
