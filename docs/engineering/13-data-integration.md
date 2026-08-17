# Data Integration Gate

## Status

DIG.1 audit and source-contract freeze is closed. DIG.2 implements the Apple
Health / HealthKit production-ingestion path at source level. Its backend is
certified only against isolated DuckDB files and its native runtime behavior
still requires physical-device/Xcode certification in DIG.5. Intervals.icu,
Zwift provenance changes, cross-source aliasing, Stage 32, and Coach behavior
are not part of DIG.2.

## HealthKit architecture

```text
HealthKit on iPhone (read only)
  -> per-type HKAnchoredObjectQuery
  -> protected local outbox with candidate anchors
  -> authenticated bounded POST
  -> HealthKitIngestionService
  -> canonical health_records
  -> existing HealthRepository / SleepBuilder
```

The iOS application requests an empty `toShare` set. The bounded read set is
HRV SDNN, resting and workout heart rate, body mass, active and basal energy,
steps, respiratory rate, oxygen saturation, sleeping wrist temperature when
available, cycling distance, cycling power/cadence when available, sleep
analysis, and workout identity/summary. Raw identifier lookup keeps optional
newer quantities compatible with the iOS 16.2/Xcode 14.2 baseline.

The app contains the HealthKit and background-delivery entitlements and only
`NSHealthShareUsageDescription`; it deliberately has no Health write usage
description. Authorization absence is never interpreted as proof that a health
sample does not exist.

## Anchors and at-least-once delivery

Each sample type owns an archived `HKQueryAnchor`. A query result's candidate
anchor is stored inside the durable pending batch. It is committed to the
separate anchor store only after an authenticated ACK with matching `batch_id`,
zero rejected records, and `safe_to_advance_anchor=true`. Network failure,
restart, or partial rejection leaves the outbox and committed anchor unchanged.

Observer queries provide best-effort hourly background triggers. Foreground
activation performs the mandatory catch-up path. Background delivery is not a
scheduler guarantee and cannot be certified on Simulator.

## Protected outbox and credential

The bounded file outbox uses atomic writes and complete-until-first-user-
authentication file protection. It stores versioned normalized records and
candidate anchor archives, not arbitrary HealthKit object dumps. Raw health
payloads are never logged. Retry uses stable batch identity and bounded
exponential delay. The ingestion credential is read from Keychain with
after-first-unlock, this-device-only accessibility; no credential is committed
to Git.

## HTTP contract

```text
POST /api/v1/ingestion/healthkit
Authorization: Bearer <device credential>
Content-Type: application/json
```

The endpoint is a controlled ingestion write and is separate from the native
GET-only read client. Production configuration uses
`HEALTHKIT_INGESTION_TOKEN`; absence disables ingestion. Authentication uses a
constant-time comparison. Request bodies and batches are bounded to 1 MB and
500 records. Operational responses/logging need only batch ID, provider,
counts, duration, and error code.

Schema activation is a separate operator-controlled call to
`initialize_healthkit_ingestion_schema(path)`. Importing or constructing the
service does not initialize production storage. The controlled production gate
must initialize the schema before enabling the token and endpoint.

Contract version `1.0` contains provider `healthkit`, stable device and batch
IDs, client creation time, and normalized records. Each record carries HealthKit
UUID, typed sample identifier, UTC start/end, canonical numeric value/unit,
bounded source/device/timezone provenance, deletion flag, and update time.
ACK contains accepted/duplicate/rejected counts, rejected references, server
receive time, and the explicit anchor-safety flag.

## Canonical units

| Fact | Unit |
|---|---|
| HRV | `ms` |
| heart/respiratory/cadence rate | `count/min` |
| body mass | `kg` |
| energy | `kcal` |
| steps | `count` |
| oxygen saturation | `fraction` |
| temperature | `degC` |
| cycling distance | `m` |
| cycling power | `W` |
| sleep stage | `category` |
| workout duration | `s` |

All transport timestamps are ISO 8601 UTC. Optional source timezone is retained
for later sleep/day grouping; backend code does not guess it.

## Persistence, identity, updates, and deletion

`health_records` remains the canonical Health store and the XML bootstrap stays
compatible. DIG.2 additively introduces `provider`, `external_id`, `deleted`,
and `updated_at`, plus a unique provider identity and an idempotent batch-audit
table. `(healthkit, HKObject.UUID)` identifies a source record. An identical
retry is a no-op; changed supported semantics deterministically replace that
source projection. A deletion retains provider identity and a value-free
tombstone row, is excluded from active Health/Sleep reads, and can support later
derived-state rebuild. DIG.2 does not implement a historical recomputation
engine.

Individual sleep-stage intervals are transported and persisted without iOS
aggregation. Existing `SleepBuilder` remains the owner of session aggregation.
`HKWorkout` is a supplemental UUID/duration fact only; it does not emit a second
`ACTIVITY_RECORDED` and does not replace Zwift FIT. Cross-source activity
aliasing remains DIG.5.

## Privacy and boundaries

HealthKit facts flow only to the canonical Health store. They are never written
to Athlete Context Memory v2. iOS performs no recovery scoring, Coach logic, or
HealthKit writes. DIG.2 adds no Intervals client, Zwift behavior, cross-source
deduplication engine, additional provider, or Stage 32 functionality.

## Certification boundary

Backend parsing, validation, authentication, idempotency, partial rejection,
update/delete, legacy XML compatibility, and downstream visibility are covered
with synthetic isolated tests. Native source covers read scope, guarded types,
anchor/outbox/ACK behavior, deterministic batches, retry, protected storage,
foreground catch-up, and background observer wiring.

The following remain physical-device/Xcode certification facts for DIG.5:

- real HealthKit authorization presentation and limited-access behavior;
- signed entitlement validation;
- actual observer background wakeups;
- anchored samples and deletions from a real Health store;
- Keychain-provisioned credential against a controlled backend;
- end-to-end foreground/background ACK and freshness timing.

## Intervals.icu supplemental activity integration (DIG.3)

DIG.3 adds one bounded, read-only backend adapter under
`integrations/intervals_icu`. It uses the official completed-activity endpoint:

```text
GET /api/v1/athlete/{athlete_id}/activities?oldest=YYYY-MM-DD&newest=YYYY-MM-DD
```

Personal access uses HTTP Basic authentication with `API_KEY` as username and
the API key as password. `INTERVALS_ATHLETE_ID` and `INTERVALS_API_KEY` are
injected through configuration; missing values produce a typed disabled state.
The secret is never logged or persisted. The client sends only GET, has a
timeout and at most three attempts, retries timeouts/transient 5xx with bounded
exponential backoff, honors a bounded `Retry-After` for 429, and never retries
401/403 or response validation failures. Tests use an injected synthetic
transport; DIG.3 performs no real provider calls.

The provider endpoint is date-range based and does not document cursor/token
pagination or an `updated_since` parameter. The service therefore divides a
bounded range into deterministic pages of at most 31 calendar days. Initial
bootstrap is limited to 90 days. Because the endpoint filters activity dates,
not update timestamps, the persisted watermark is the last successfully
scanned time and subsequent calls scan seven days of activity-date overlap.
Provider `updated_at` remains per-record correction evidence. The caller
supplies attempt/completion time. A page or
transaction failure retains the prior watermark; advancement occurs in the
same transaction as the complete fetched slice.

The versioned normalized record is identified by
`(provider=intervals_icu, external_id=activity.id)`. It retains UTC start/end,
bounded sport mapping, duration, distance, selected optional HR/power/cadence
summaries, provider update time, archived/tombstone state when supplied, and a
semantic fingerprint. Unknown optional response fields are ignored and an
unknown sport maps to `OTHER`. Non-finite, negative, or implausibly unbounded
numeric values are rejected. Full arbitrary provider JSON is not stored.

### Ownership and metric names

Intervals activity rows are supplemental source facts prepared for later DIG.5
reconciliation. They do not emit `ACTIVITY_RECORDED`, replace a Zwift/FIT
activity, deduplicate across sources, or write Athlete Context Memory. Planned
calendar events are not fetched and can never replace the canonical Training
Plan.

Provider load is named `intervals_external_tss` and provider intensity is named
`intervals_external_intensity`. No Intervals value overwrites platform-owned
FIT-derived NP/IF/TSS or platform ATL-like, CTL-like, and TSB/form calculations.
The provider-specific read model therefore cannot be confused with the
existing training-load DTO.

### Persistence and audit

The operator-controlled, idempotent schema initializer creates only:

- `intervals_icu_activities`, the current normalized source projection;
- `intervals_icu_sync_state`, containing watermark, last attempt, last success,
  and typed last error code;
- `intervals_icu_sync_audit`, containing bounded counts, timestamps, status,
  and before/after watermarks (never raw activities or secrets).

Same identity and semantics is a no-op; changed semantics is a deterministic
update. Provider archived/deleted state is retained as a source tombstone and
does not delete a canonical platform activity. Sync results report fetched,
inserted, updated, unchanged, archived, rejected, watermarks, caller-supplied
timestamps, and provider status.

DIG.3 deliberately adds no scheduler or runtime composition. The service is
ready for a later controlled 4–6 hour / pre-morning-runtime invocation, but it
is not activated. It also adds no generic HTTP framework, no HealthKit changes,
no Zwift acquisition/provenance changes, no alias engine, no UI, and no Stage 32
behavior.

## Explicit Zwift FIT provider (DIG.4)

DIG.4 preserves the standard generic FIT pipeline and adds a bounded adapter
for files acquired through an explicitly configured Zwift Activities folder:

```text
ZWIFT_ACTIVITY_SOURCE_PATH
  -> ZwiftFitArtifactDiscovery
  -> SHA-256 artifact identity (provider=zwift_fit)
  -> StandardFitWorkoutIngestionService
  -> FitParser / ActivityFactory / WorkoutAnalyzer
  -> content-keyed workout row
  -> CanonicalActivityCandidate
  -> StandardActivityFactSynchronizationService
  -> ACTIVITY_RECORDED(source_type=zwift_fit)
```

There is no core default for `ZWIFT_ACTIVITY_SOURCE_PATH`. Absence or a missing
directory is a typed unavailable provider state. The legacy
`FIT_ACTIVITY_SOURCE_PATH` remains the generic `fit_file` input and retains its
backward-compatible local-development default. A FIT is identified as Zwift
only because it passed through the explicit folder adapter—never because of its
name, sport, activity text, or another heuristic.

Discovery considers regular `.fit` files case-insensitively, skips hidden/temp,
non-FIT, directory, zero-byte, and older-than-bootstrap artifacts, and sorts by
mtime then name. A file must be at least 60 seconds old before it is ready,
preventing ingestion while Zwift is still writing it. Initial discovery is
bounded to 90 days and at most 500 recent artifacts. Re-scans consult the known
content-hash store; a late copied artifact receives a recent mtime and enters
the bounded window without relying on activity start time. DIG.5 may schedule
bounded scans frequently enough to certify the target completion-to-ingestion
freshness of 15 minutes; DIG.4 does not activate polling or runtime ordering.

Raw artifact identity is `sha256:<digest of all FIT bytes>`. The provider
identity is `(zwift_fit, artifact_hash)`. Rename, copy, or repeat scan is a
no-op. Different bytes under the same filename are a new artifact. Content
identity is also used as the additive workout storage key, while existing
filename-based generic/manual APIs remain compatible.

The provider audit retains only hash, basename reference, size, source mtime,
ingestion time, storage key, normalized candidate JSON, and its deterministic
fingerprint. It never exposes the absolute user filesystem path or raw FIT
bytes. Per-scan audit contains bounded counts. One malformed FIT becomes a
typed per-artifact failure and does not stop later valid files.

`CanonicalActivityCandidate` is the neutral DIG.5-facing projection. It carries
provider/external identity, UTC start/end, duration, existing sport semantics,
distance, FIT-derived NP/IF/TSS, artifact fingerprint/reference, ingestion time,
and deterministic `HIGH_FIDELITY` trust. FIT remains canonical owner of the
Zwift activity's power, cadence, HR, distance, duration, NP, IF, and TSS.
Intervals and HealthKit remain supplemental.

DIG.4 does not merge Zwift, HealthKit, or Intervals candidates. It adds no HTTP
endpoint, filesystem watcher, scheduler, direct/private Zwift API, Zwift
credentials, Strava fallback, Coach behavior, or Stage 32 behavior. The sync
service is ready for DIG.5 to place before activity fact synchronization and
assessment without changing the currently frozen runtime sequence now.

## Cross-source activity identity and certification (DIG.5)

One physical Zwift activity observed by `zwift_fit`, `intervals_icu`, and
`healthkit` becomes one Zwift-based canonical group. Its stable ID is a SHA-256
projection of provider and external ID. Original provider identities remain as
aliases with match method, bounded evidence, and reconciliation time.

Frozen priority is Zwift FIT, Intervals.icu, HealthKit, but priority applies
only after matching. Real explicit linkage wins. Otherwise a deterministic
candidate requires compatible normalized sport, UTC start within ±120 seconds,
and duration difference no greater than max(60 seconds, 5%). Distance is
supporting evidence. Zero candidates is `UNMATCHED`; multiple candidates is
`AMBIGUOUS` and never auto-merged; a repeated alias is `ALREADY_MATCHED`.

Supplemental-only records do not create completed activities in v1. When Zwift
arrives later it becomes canonical and earlier records become aliases. Only
Zwift emits `ACTIVITY_RECORDED`, preventing doubled activity count, FIT TSS,
assessment, execution, and briefing. This precedes and remains separate from
planned-session/completed-activity reconciliation.

Additive transactional tables are `canonical_activity_identities`,
`canonical_activity_aliases`, `activity_reconciliation_audit`, and
`data_provider_freshness`. FIT retains duration, distance, HR, power, cadence,
NP, IF, and TSS ownership. Intervals metrics remain explicitly external;
HealthKit remains supplemental for workout identity and canonical for daily
health. HealthKit optionally transports `workout_sport` directly from
`HKWorkoutActivityType`; no sport is inferred.

Provider operation is failure-isolated as `DISABLED`, `READY`, or `DEGRADED`.
Freshness is `FRESH`, `STALE`, `UNAVAILABLE`, or `NEVER_SYNCED`. Targets are
HealthKit morning ≤6 h, HealthKit workout best effort ≤30 min, Intervals ≤6 h,
and stable Zwift artifact ≤15 min. Runtime-ready order is source sync,
ingestion, cross-source reconciliation, activity facts, plan reconciliation,
assessment, decision, prescription, continuity, adaptation, briefing, and
publication. It is not activated in source certification.

### Pending operator gates

1. **Gate A:** back up and verify production DBs, then explicitly initialize
   HealthKit additions, Intervals, Zwift audit, and the four identity/freshness
   tables. No destructive migration.
2. **Gate B:** inject Intervals athlete ID/API key without printing secrets;
   run one bounded sync and verify audit/freshness.
3. **Gate C:** operator confirms `ZWIFT_ACTIVITY_SOURCE_PATH`; run one bounded
   read scan and verify stability, hash idempotency, and freshness.
4. **Gate D:** physical-iPhone signing/capability, read-only permission sheet,
   real anchored sample, protected outbox, backend ACK, anchor advancement, and
   foreground catch-up. Background delivery is best-effort observation.

Until these pass: **DIG.5 SOURCE CERTIFICATION PASS — OPERATOR GATES PENDING**.
There is no direct Zwift API, Strava, Stage 32, Coach, or new native feature.

### Read-only source status

`GET /api/v1/data-sources/status` returns exactly HealthKit, Intervals.icu, and
Zwift operational/freshness state with contract version `1.0`. Fields are
bounded to provider, typed states, UTC attempt/success times, safe error code,
and freshness target. It exposes no secrets, athlete ID, health values, raw
payloads, database paths, or filesystem paths. Provider reads are isolated;
missing configuration is HTTP 200 with `DISABLED` / `NEVER_SYNCED`.

The native More screen presents these backend-owned facts as three accessible
text rows and formats the optional UTC success timestamp in the user's locale.
Endpoint failure affects only this section. Reading status never initializes a
schema, calls a provider, scans the Zwift folder, triggers sync, or writes data.
