# Architecture Baseline v1

## Purpose

Athlete Platform is a modular monolith for collecting athlete data, planning
training, analysing workout execution, and building deterministic analytical
views of training history.

The architecture favours:

- deterministic domain engines with typed inputs and outputs;
- clear bounded contexts instead of a single global processing layer;
- immutable analytical results where practical;
- an AI Coach as a future consumer of prepared facts, not as an engine that
  calculates domain analytics or makes hidden decisions.

Athlete Memory is an append-only analytical memory for selected athlete events.
It is not full Event Sourcing for the entire system: it does not replace the
operational health, training, or planning repositories.

## Bounded Contexts

### Ingestion

Owns source-specific parsing and conversion into domain `Activity` objects.

- `collectors/apple_health/`
- `training/parsers/`
- `training/ingestion/`
- `training/factories/`

### Health & Recovery

Builds health context and recovery/performance state used for training
decisions.

- `repositories/health_repository.py`
- `engines/context_builder.py`
- `health/`
- `recovery/`
- `performance/`

### Training Planning

Produces a planned workout from athlete state, diagnosis, prescription,
selection, recipes, DSL, and timeline construction.

- `decision/`
- `planner/`
- `workout/`
- `timeline/`
- `optimizer/`
- `simulator/`

### Workout Execution

Analyses a completed activity against a planned workout and produces technical
execution results and deterministic athlete feedback.

- `training/analysis/`
- `execution/`
- `feedback/`
- `pipeline/post_workout.py`

### Athlete Memory & Analytics

Stores selected completed-workout facts, projects them into typed read-side
observations, and calculates pure training analytics.

- `athlete/memory/`
- `schema/athlete_memory_schema.py`

### Review

Composes prepared analytical reports into period-based typed review models.

- `athlete/review/`

### Presentation

Contains console, HTML, export, and demonstration-facing output code. It is
not a source of domain decisions.

- `briefing/`
- `coach/`
- `renderers/`
- `scripts/`

## Existing Workflows

The repository currently has multiple explicit workflows. They are not yet
joined by one runtime entry point.

### A. Health Context Workflow

```text
AppleHealthImporter / HealthRepository
        → ContextBuilder
        → RecoveryEngine / PerformanceEngine
        → AthleteState
```

Relevant implementation includes `collectors/apple_health/`,
`repositories/health_repository.py`, `engines/context_builder.py`,
`recovery/engine.py`, and `performance/engine.py`.

### B. Training Planning Workflow

```text
AthleteState
        → PlatformEngine
        → DecisionEngine
        → PlannerEngine
        → Optimizer / Simulator / Timeline
```

`pipeline/engine.py` orchestrates this planning workflow. `DecisionEngine`
uses diagnosis, prescription, and decision selection. `PlannerEngine` selects
a recipe and compiles it through the training DSL.

### C. Post-Workout Analysis Workflow

```text
Workout + Activity
        → PostWorkoutPipeline
        → WorkoutSummary
        → ExecutionResult
        → WorkoutFeedback
```

`pipeline/post_workout.py` orchestrates summary analysis, timeline building,
execution analysis, and feedback generation. It returns `PostWorkoutResult`.

### D. Memory Analytics & Review Workflow

```text
AthleteMemoryEvent
        → AthleteMemoryReader
        → AthleteMemorySnapshot
        → TrendEngine / PatternDetector
        → WeeklyReviewService
```

`athlete/memory/` owns the append-only event store, read-side projection, and
pure analytics. `athlete/review/` only composes existing trend and pattern
reports.

## Workflow Boundaries

The following separations are intentional:

- `PostWorkoutPipeline` does not yet write to Athlete Memory.
- `WeeklyReviewService` does not run `AthleteMemoryReader`, `TrendEngine`, or
  `PatternDetector`; it receives ready reports.
- There is no single runtime entry point joining health, planning,
  post-workout analysis, Memory, analytics, and review.

These are deliberate boundaries that preserve independent, testable workflows;
they are not an absence of architecture. A future application workflow may
compose them without moving analytical or persistence logic into the existing
engines.

## Module Lifecycle Status

### CURRENT

- `pipeline/post_workout.py`
- `pipeline/engine.py`
- `planner/`
- `decision/selection/`
- `athlete/memory/`
- `athlete/review/`
- `athlete/models.py`
- `engines/trend_engine.py`

### LEGACY / ISOLATED

- `planning/`
- `core/trend/`
- `briefing/`
- `workout/export/`
- `execution/adapter.py`

### EXPERIMENTAL

- `coach/morning_briefing.py`
- `core/results.py`

### UNKNOWN / INVESTIGATE

- `workout/exporters/`
- `briefing/engine.py`

Lifecycle status documents the current architecture baseline. It does not by
itself remove, rename, or deprecate any public API.

## Known Architectural Risks

- `AthleteState` may become a God Object if it absorbs memory, history,
  assessments, plans, and presentation concerns.
- `PlatformEngine` may grow beyond planning orchestration and become a global
  application coordinator.
- A future Knowledge Engine could become a cross-cutting God Object if it
  reads repositories, performs analytics, makes decisions, and renders output.
- Multiple public names have overlapping meanings.
- Direct repository access in legacy health flows can be mixed accidentally
  with the Memory read-side pattern.
- Some demonstration scripts still target older contracts.

## Naming Conflicts

| Name | Existing meanings |
|---|---|
| `TrendEngine` | Training analytics in `athlete/memory/`; health trend metrics in `engines/`; unused trend-context builder in `core/trend/`. |
| `SelectionEngine` | Prescription-to-plan selection in `decision/`; recipe selection in `planner/`. |
| `MorningBriefing` | Distinct legacy models in `briefing.models` and `core.results` (LEGACY). The canonical domain model is `morning_briefing.domain.MorningBriefing` (Stage 20). Frontend wire-format is `MorningBriefingWire` in `morning-briefing-api-types.ts`. |
| Planning / Planner | Static weekly planning in `planning/`; recipe and DSL-based workout construction in `planner/`. |
| `workout/export` / `workout/exporters` | Active older ZWO exporter path and a separate currently unpopulated exporter namespace. |

## Rules for Future Development

- Model new analytics as: domain snapshot → pure analytics → typed report.
- Analytics modules must not access DuckDB or repositories.
- `DecisionEngine` must not read repositories or Athlete Memory directly.
- AI Coach must not calculate analytics; it consumes typed facts and reports.
- Compositional services combine ready typed results only; they do not repeat
  analytics or persistence work.
- New domains must not automatically copy the legacy Health architecture.
- No new module may depend on a LEGACY or EXPERIMENTAL module without an
  explicit architectural decision.

## Planned, Not Yet Implemented

- An application workflow connecting `PostWorkoutResult` to
  `AthleteMemoryWriter`.
- `TrainingAssessment`.
- `AthleteAssessment`.
- A typed Knowledge Context for downstream consumers.
- Adaptation Engine.
- AI Coach integration.

## Legacy Architecture Context

Earlier documentation described a SQLite-centered four-layer flow ending in a
Morning Briefing. That description is retained only as historical context: the
current repository uses DuckDB and now contains separate execution, feedback,
Athlete Memory, analytics, and review workflows.

## Registry Consistency Quality Gate

In order to keep the system aligned, the CI validation pipeline enforces strict consistency between the `Biomarker Registry` (definitions of available markers) and the `Medical Rule Registry` (rules interpreting trends).

* **RegistryConsistencyError (Errors):** Automatically blocks the build/CI. This happens when a specialist rule is registered for a code that has no corresponding active biomarker definition in the registry.
* **Warnings:** Informational only. They highlight active biomarkers in the registry that lack dedicated specialist rules (falling back to generic rules). These do not block CI.

### Running Validation Locally

To run the consistency checks locally, run the CLI utility:
```bash
python -m scripts.validate_biomarker_registry_consistency
```

## Morning Briefing HTTP API

### Endpoint

```
GET /api/v1/morning-briefing
```

Returns a Morning Briefing aggregate for the current day.
The response is always HTTP 200 unless the data source is explicitly unavailable (HTTP 503).
A missing or empty briefing is not an error — it returns `status: unavailable` with an empty `sections` array.

### Pipeline

```
MorningBriefingInputProvider
        ↓
MorningBriefingBuilder       (domain assembly, section mapping)
        ↓
MorningRecommendationEngine  (deterministic rules, no LLM)
        ↓
MorningBriefingSerializer    (JSON-safe dict, ISO 8601, lowercase enums)
        ↓
HTTP JSON response
```

### Status semantics

| Status | Meaning |
|---|---|
| `ready` | All three sections (Recovery, Training, Biomarkers) are available and no section is stale. |
| `partial` | At least one section is available, but at least one is missing (e.g. training not planned or unavailable). |
| `stale` | Data exists, but `recovery.is_stale` or `biomarkers.is_stale` is `true`. Takes precedence over `ready`/`partial`. |
| `unavailable` | No sections were produced (all input fields are `None`). |

### Dependency injection

The endpoint receives its data via a `MorningBriefingInputProvider` injected into
`create_dashboard_wsgi_app(morning_briefing_provider=...)`. When no provider is given,
`EmptyMorningBriefingInputProvider` is used as a safe default (returns `unavailable`).
Production providers are injected at composition time without modifying domain logic.

### Error handling

| Condition | HTTP |
|---|---|
| Provider raises `MorningBriefingInputError` | `503 Service Unavailable` — safe error message, no technical details exposed. |
| Unexpected exception | `500 Internal Server Error` — consistent with other endpoints. |

## Morning Briefing Frontend (Stage 20)

### Module structure

```
web/AthleteWeb/src/morning-briefing/
  api/
    morning-briefing-api-types.ts      ← wire-format + validated types
    morning-briefing-api-client.ts     ← MorningBriefingApiClient, validateMorningBriefingPayload
  dashboard-card/
    morning-briefing-card-types.ts     ← CardState, pickTopRecommendation, statusLabel, formatGeneratedAt
    morning-briefing-card-presentation.ts  ← pure DOM factory, no fetch
    morning-briefing-card-container.ts ← orchestrator: fetch → CardState → render
    morning-briefing-card.css
  full-screen/
    morning-briefing-full-screen-presentation.ts  ← pure DOM factory, no fetch
    morning-briefing-full-screen-container.ts     ← orchestrator: fetch → FullScreenState → render
    morning-briefing-full-screen.css
```

### Architecture contract

```
GET /api/v1/morning-briefing
        ↓
MorningBriefingApiClient       (fetch, timeout, runtime validation)
        ↓
MbApiResult                    (success | failure, typed error type)
        ↓
Container (Card or FullScreen) (state machine, retry, onBack/onOpen callbacks)
        ↓
Presentation                   (pure DOM factory, no HTTP, no domain logic)
```

### Routing

| URL param | ApplicationView | Handler |
|---|---|---|
| (none) | `"morning-briefing"` | legacy Dashboard (DuckDB/JSON preview) |
| `?view=morning-briefing-detail` | `"morning-briefing-detail"` | `MorningBriefingFullScreenContainer` |

Navigation flow: Dashboard Card `onOpen` → `openMorningBriefingDetail()` in `main.ts` → `pushState` → `renderPreview()` → Full Screen. Back button → `openMorningBriefing()` → `window.history.back()`.

### Rules

- Presentation layer must not execute fetch or know HTTP status codes.
- Containers must not render unvalidated payload sections.
- `validateMorningBriefingPayload` is the single validation boundary — not duplicated.
- `statusLabel` and `formatGeneratedAt` helpers are defined once in `morning-briefing-card-types.ts` and reused by both Card and Full Screen.
- No global cache. Each container fetches independently on mount.

## Performance Lab HTTP API (Stage 21)

### Endpoint

```
GET /api/v1/performance-lab/history
```

Returns the performance test history read model for the athlete.

### Pipeline

```
PerformanceTestSessionProvider
        ↓
PerformanceTestHistoryBuilder     (deduplication, chronological sorting oldest → newest)
        ↓
LactateCurveBuilder               (optional: strictly for LACTATE_STEP_TEST)
        ↓
LactateThresholdAnalyzer          (optional: fixed 2.0 / 4.0 mmol/L threshold detection)
        ↓
PerformanceTestHistorySerializer  (JSON-safe dict, ISO 8601, lowercase enums)
        ↓
HTTP JSON response (200 OK)
```

### Key Semantics

- **Chronological Ordering:** History entries are sorted from oldest to newest by `session.performed_at` (tie-breaker: `test_id` ascending).
- **Deduplication:** Multiple sessions with the same `test_id` are deduplicated to keep the newest `performed_at`.
- **Lactate Analysis Boundary:** `lactate_curve` and `threshold_analysis` are generated strictly for `LACTATE_STEP_TEST`. For other test types (`FTP_TEST`, `FIELD_TEST`, `CARDIOPULMONARY_EXERCISE_TEST`), both fields are `null`.
- **Current Threshold Method:** Threshold detection currently uses the fixed 2.0 / 4.0 mmol/L method (`fixed_2_mmol`, `fixed_4_mmol`).

### Dependency Injection

The endpoint receives sessions via `PerformanceTestSessionProvider` injected into
`create_dashboard_wsgi_app(performance_lab_provider=...)`. Default is `EmptyPerformanceTestSessionProvider` (returns `{"entries": []}`).

### Error Handling

| Condition | HTTP Status | Response |
|---|---|---|
| Success | `200 OK` | `{"entries": [...]}` |
| Empty provider | `200 OK` | `{"entries": []}` |
| Provider raises `PerformanceTestSessionProviderError` | `503 Service Unavailable` | `{"error": "Performance Lab data source is temporarily unavailable."}` |
| Unexpected exception | `500 Internal Server Error` | `{"error": "Internal server error fetching Performance Lab history."}` |


## Decision Intelligence 2.0 HTTP API

The Decision Intelligence 2.0 subsystem exposes its latest ready audit record via the HTTP endpoint:

`GET /api/v1/decision-intelligence/latest`

### Pipeline & Boundary Architecture

```
DecisionAuditRecordProvider protocol (Dependency Injection)
        ↓
get_latest_record() -> DecisionAuditRecord | None
        ↓
DecisionAuditRecordSerializer (JSON-safe dict, ISO 8601, lowercase enums)
        ↓
HTTP JSON response (200 OK)
```

### Key Semantics

- **No On-Demand Decision Execution:** The HTTP route layer does NOT execute `DecisionPolicyV2` or rebuild `AthleteDecisionContext`. It exclusively exposes a pre-built, ready `DecisionAuditRecord`.
- **Null Decision Semantics:** When no decision record exists (provider returns `None`), the endpoint returns `HTTP 200 OK` with payload `{"decision": null}`. Missing decision is not an HTTP error.
- **Contract Schema:** The root JSON payload always contains the single top-level key `"decision"`. Inside, it serializes `context`, `policy_result` (`action`, `severity`, `signals`, `confidence`, `policy_version`), and `recommendation_plan` (`recommendations`, `explanation`).
- **Privacy & Security Boundary:** Raw database queries, file paths, tracebacks, internal class names, and raw biomarker/lab payloads are strictly stripped from the public API contract.

### Dependency Injection

The WSGI factory accepts an optional `decision_audit_provider` parameter:
`create_dashboard_wsgi_app(decision_audit_provider=...)`. Default is `EmptyDecisionAuditRecordProvider` (returns `{"decision": null}`).

### Error Handling

| Condition | HTTP Status | Response |
|---|---|---|
| Success (record available) | `200 OK` | `{"decision": {...}}` |
| Success (no record available) | `200 OK` | `{"decision": null}` |
| Provider raises `DecisionAuditRecordProviderError` | `503 Service Unavailable` | `{"error": "Decision Intelligence data source is temporarily unavailable."}` |
| Unexpected exception | `500 Internal Server Error` | `{"error": "Internal server error fetching Decision Intelligence record."}` |


## Decision Intelligence 2.0 Application Execution Service

The `DecisionExecutionService` class in `decision/execution_service.py` provides the application orchestrator for executing the complete Decision Intelligence 2.0 pipeline in a single stateless invocation.

### Orchestration Pipeline

```
DecisionExecutionRequest(decision_id, generated_at, recorded_at)
        ↓
AthleteDecisionContextProvider.build_context(generated_at)
        ↓
AthleteDecisionContext
        ↓
DecisionPolicyV2.evaluate(context)
        ↓
DecisionPolicyResult
        ↓
RecommendationPlanBuilder.build(policy_result)
        ↓
RecommendationPlan
        ↓
DecisionAuditRecordBuilder.build(...)
        ↓
DecisionAuditRecord
        ↓
DecisionExecutionResult(request, record)
```

### Key Semantics

- **Pure Application Orchestration:** The service does NOT invoke `datetime.now()`, generate `UUID`s, perform DuckDB/database persistence, or execute HTTP/I/O logic. All timestamps and identifiers are provided explicitly via `DecisionExecutionRequest`.
- **Stateless & Deterministic:** Multiple executions with identical requests and deterministic context providers return strictly equal `DecisionExecutionResult` instances.
- **Error Propagation:** Exceptions raised by the context provider, policy evaluator, or builders propagate directly without being swallowed or wrapped in generic exceptions.
- **Deferred Persistence:** `DecisionExecutionService` returns the fully constructed `DecisionAuditRecord`, but does NOT persist it to DuckDB (persistence is introduced in subsequent Stage 23 sprints).


## Decision Intelligence 2.0 Real Context Adapters

The `decision/context_adapters/` module bridges domain read models from existing platform subsystems to neutral `AthleteDecisionContext` snapshots.

### Adapter Pipeline Architecture

```
MorningBriefingInputProvider → RecoveryDecisionContextAdapter → RecoveryDecisionContext
MorningBriefingInputProvider → TrainingDecisionContextAdapter → TrainingDecisionContext
MorningBriefingInputProvider → BiomarkerDecisionContextAdapter → BiomarkerDecisionContext
PerformanceTestSessionProvider → PerformanceDecisionContextAdapter → PerformanceDecisionContext
        ↓
RuntimeAthleteDecisionContextProvider
        ↓
AthleteDecisionContextBuilder
        ↓
AthleteDecisionContext
```

### Context Status Semantics

- **`AVAILABLE`**: The source provider returned complete, valid data for the target decision context.
- **`PARTIAL`**: The source provider delivered a record, but required key fields (e.g. `recovery_score`) are missing.
- **`STALE`**: The source provider explicitly flagged data as stale (`is_stale = True`).
- **`UNAVAILABLE`**: The source provider has no data or raised an expected provider error (`MorningBriefingInputError`, `PerformanceTestSessionProviderError`).

### Single Snapshot Fetch Semantics

- **Single Fetch per Build:** `RuntimeAthleteDecisionContextProvider` fetches `MorningBriefingInput` exactly ONCE per `build_context()` call and passes the request-scoped snapshot to the Recovery, Training, and Biomarker adapters.
- **Error Propagation:** Expected domain provider errors (`MorningBriefingInputError`, `PerformanceTestSessionProviderError`) map cleanly to `ContextDataStatus.UNAVAILABLE`. Unexpected errors (`TypeError`, `ValueError`, `RuntimeError`) propagate without being swallowed.
- **No Recalculation:** Adapters do NOT re-run recovery score calculations, lactate threshold analysis (`LactateThresholdAnalyzer`), or biomarker classification rules.
- **Strict Protocol Isolation:** `RuntimeAthleteDecisionContextProvider` consumes only neutral `*DecisionContextAdapter` protocols without importing raw bounded context domain models.


## Decision Intelligence 2.0 Runtime Workflow & Composition Root

The `DecisionRuntimeWorkflow` class in `decision/runtime_workflow.py` and factory `create_decision_runtime_workflow` in `decision/runtime_composition.py` orchestrate non-deterministic runtime concerns (clock, UUID) and assemble the production dependency graph.

### Workflow & Composition Flow

```
DecisionClock (SystemUtcDecisionClock)
DecisionIdGenerator (UuidDecisionIdGenerator)
        ↓
DecisionRuntimeWorkflow.run()
        ↓
DecisionExecutionRequest(decision_id="decision-<uuid>", generated_at=t1, recorded_at=t2)
        ↓
DecisionExecutionService.execute(request)
        ↓
RuntimeAthleteDecisionContextProvider (Shares 1 MorningBriefingInput snapshot)
        ↓
DecisionAuditRecord & DecisionExecutionResult
```

### Key Semantics

- **Explicit Protocol Boundaries:** `DecisionClock` (`now() -> datetime`) and `DecisionIdGenerator` (`generate() -> str`) isolate time and ID generation. Test cases inject deterministic stubs.
- **Timestamp Capture Order:** `generated_at` is captured immediately prior to ID generation; `recorded_at` is captured immediately prior to pipeline execution (`clock.now()` is called twice per `run()`).
- **Composition Root Factory:** `create_decision_runtime_workflow(morning_briefing_provider, performance_test_provider)` wires production adapters and `DecisionExecutionService` without executing I/O upon creation.
- **Stateless Runtime Execution:** `DecisionRuntimeWorkflow` stores no execution history. Consecutive `run()` calls generate fresh requests and pipeline executions.
- **Error Propagation:** Exceptions raised by the context provider, policy evaluator, or builders propagate directly without being swallowed or wrapped in generic exceptions.


## Decision Intelligence 2.0 DuckDB Audit Record Repository

The `DuckDbDecisionAuditRecordRepository` class in `decision/persistence/duckdb_repository.py` provides thread-safe, append-only DuckDB persistence for `DecisionAuditRecord` instances.

### Table Schema (`decision_audit_records`)

| Column | SQL Type | Constraint | Description |
|---|---|---|---|
| `decision_id` | `VARCHAR` | `PRIMARY KEY` | Unique decision identifier |
| `generated_at` | `TIMESTAMP` | `NOT NULL` | Context creation timestamp (UTC) |
| `recorded_at` | `TIMESTAMP` | `NOT NULL` | Audit request creation timestamp (UTC) |
| `action` | `VARCHAR` | `NOT NULL` | Decision action (`proceed`, `reduce`, etc.) |
| `severity` | `VARCHAR` | `NOT NULL` | Severity (`low`, `medium`, `high`, `critical`) |
| `confidence` | `DOUBLE` | `NOT NULL` | Numeric confidence (0.0 to 1.0) |
| `policy_version` | `VARCHAR` | `NOT NULL` | Policy version string (e.g. `"2.0"`) |
| `record_schema_version` | `VARCHAR` | `NOT NULL` | Schema version (`"1.0"`) |
| `payload_json` | `VARCHAR` | `NOT NULL` | Canonical JSON string payload |

### Key Semantics & Boundaries

- **Metadata Validation:** `get_by_id`, `get_latest`, and `list_records` validate that all index metadata columns (`decision_id`, `generated_at`, `recorded_at`, `action`, `severity`, `confidence`, `policy_version`, `record_schema_version`) strictly match the decoded `payload_json`. Discrepancies or tampering raise `DecisionAuditRecordDataError`.
- **Timezone UTC Preservation:** Datetime values are strictly stored and retrieved in timezone-aware UTC (`_to_naive_utc` / `_to_aware_utc`).
- **Connection Ownership:** `DuckDbDecisionAuditRecordRepository` supports external connection injection and does NOT close connections it did not create.
- **Deterministic Read Ordering:**
  - `get_latest()` orders by `generated_at DESC, decision_id DESC LIMIT 1`.
  - `list_records()` returns all records ordered by `generated_at ASC, decision_id ASC` (*oldest $\rightarrow$ newest*).
- **Canonical JSON Codec:** `DecisionAuditRecordCodec` utilizes `DecisionAuditRecordSerializer` to produce deterministic, sorted-key JSON strings without relying on `pickle` or Python `eval()`.
- **Explicit Call Boundary:** `DecisionRuntimeWorkflow` does NOT automatically invoke `save()`. Repositories are called explicitly by application workflows or background tasks.


## Persisted Decision Runtime Workflow & Repository Provider

Sprint 23.5 connects the runtime workflow, persistence, and HTTP API into a complete vertical pipeline without executing decision policies during HTTP GET requests.

### End-to-End Pipeline

```
Real Source Providers (Morning Briefing & Performance Lab)
        ↓
create_persisted_decision_runtime_application(...)
        ↓
PersistedDecisionRuntimeWorkflow.run()
        ↓
DecisionRuntimeWorkflow.run() → DecisionExecutionResult
        ↓
DecisionAuditRecordRepository.save(result.record)  [Atomic append-only DuckDB persistence]
        ↓
RepositoryDecisionAuditRecordProvider.get_latest_record()
        ↓
GET /api/v1/decision-intelligence/latest
        ↓
AthleteWeb AI Coach Experience
```

### Key Semantics & Architectural Guarantees

- **Neutral WSGI Factory vs Production Composition:**
  - `create_dashboard_wsgi_app(...)` is purely neutral and executes ZERO database I/O by default (defaults to `EmptyDecisionAuditRecordProvider` and `EmptyDecisionHistoryProvider`).
  - `create_production_dashboard_wsgi_app(...)` wires `DuckDbDecisionAuditRecordRepository` with shared `RepositoryDecisionAuditRecordProvider` and `RepositoryDecisionHistoryProvider` for production.
- **CWD-Independent Path Resolution:** `get_default_decisions_db_path()` resolves `data/database/decisions.duckdb` relative to `PROJECT_ROOT` rather than `os.getcwd()`.
- **Source Providers Limitation:** In the current platform state, `EmptyMorningBriefingInputProvider` and `EmptyPerformanceTestSessionProvider` are used by the CLI runner when no data source is provided, evaluating to `REVIEW / HIGH / 0.85`. No fake or synthetic data is generated.


## Decision Intelligence 2.0 Decision History HTTP API

The `GET /api/v1/decision-intelligence/history` endpoint exposes the complete immutable decision audit record history stored in `DecisionAuditRecordRepository`.

### Pipeline & Architectural Guarantees

```
DecisionAuditRecordRepository.list_records()
        ↓
RepositoryDecisionHistoryProvider.get_history() → DecisionHistory (records: oldest → newest)
        ↓
DecisionHistorySerializer.serialize(history) → {"records": [...], "count": N}
        ↓
GET /api/v1/decision-intelligence/history
```

### Key Semantics

- **Stateless HTTP GET:** `GET /api/v1/decision-intelligence/history` delegates exclusively to `RepositoryDecisionHistoryProvider.get_history()`. It does NOT execute `DecisionRuntimeWorkflow`, run `DecisionPolicyV2`, fetch source data, or modify DuckDB.
- **Shared Repository Instance:** Production server composition (`create_production_dashboard_wsgi_app`) shares a single `DuckDbDecisionAuditRecordRepository` instance between the latest provider and history provider.
- **Deterministic Read Ordering:** History records are ordered strictly by `context.generated_at ASC, decision_id ASC` (*oldest $\rightarrow$ newest*).
- **JSON Safety & Reuse:** `DecisionHistorySerializer` delegates each record serialization to `DecisionAuditRecordSerializer.serialize()`, guaranteeing identical field names and types.
- **Empty History HTTP 200:** An empty history returns HTTP 200 with `{"history": {"records": [], "count": 0}}`.
- **Provider Error Mapping:** `RepositoryDecisionHistoryProvider` maps repository errors to `DecisionHistoryProviderError`, resulting in a safe HTTP 503 response.
- **No Pagination:** The current sprint exposes the complete history without query parameter pagination or filtering.








## AthleteWeb AI Coach Experience

The frontend Decision Intelligence experience (AI Coach) displays the pre-computed decision audit record exposed by `GET /api/v1/decision-intelligence/latest`.

### Architecture & UI Boundaries

```
GET /api/v1/decision-intelligence/latest
        ↓
DecisionIntelligenceApiClient (Typed client + runtime validation)
        ↓
DecisionIntelligenceContainer (State machine: loading | empty | ready | failure | network_error | invalid_data)
        ↓
DecisionIntelligencePresentation (Pure DOM rendering: Hero Card → Recommendations → Explainability → Context Grid)
```

### Key Semantics

- **No Frontend Decision Policy Execution:** The UI layer does NOT evaluate decision rules or modify recommendations. It exclusively renders the pre-computed audit record returned by the API.
- **Strict Runtime Validation:** `validateDecisionAuditRecord` validates structure, ISO dates, allowed enums, numeric bounds, and cross-field consistency. Inconsistent payloads trigger `invalid_data` error state without rendering unsafe partial data.
- **Empty State (`decision: null`):** When `decision` is `null`, the UI displays a clean empty state (`No decision is available yet`) rather than an error.
- **Accessibility & Design System:** Implements single `<h1>`, semantic `role="status"` and `role="alert"`, keyboard navigation, and utilizes established CSS design tokens with full light/dark mode support.
- **Independent Decision History Section:** Below the latest decision hero section, `DecisionHistoryContainer` fetches `GET /api/v1/decision-intelligence/history` and renders historical records with independent state management (loading, empty, ready, failure, network_error, invalid_data).
- **UI Order Reversal:** Records arrive from API ordered *oldest $\rightarrow$ newest* (`generated_at ASC, decision_id ASC`). The UI presentation mapper reverses them to display *newest $\rightarrow$ oldest* for optimal athlete readability.
- **Read-Only Experience:** The UI provides an explicit "Odśwież historię" refresh button, but contains zero execution controls, POST endpoints, or client-side decision generation logic.


### Stage 23 Decision Intelligence 2.0 Subsystem Boundaries & Guarantees

The Decision Intelligence 2.0 subsystem is fully built, persisted, and integrated across backend and frontend layers:

1. **Persistent DuckDB Decision Repository:** `DuckDbDecisionAuditRecordRepository` provides thread-safe append-only persistence to `data/database/decisions.duckdb`.
2. **HTTP Decision History Query Endpoint:** `GET /api/v1/decision-intelligence/history` serves the complete immutable decision history read model.
3. **Independent Latest & History View States:** Latest decision and Decision History operate with isolated state machines in AthleteWeb AI Coach experience.

3. **No On-Demand Execution via HTTP Request:** The HTTP route layer does NOT invoke `DecisionPolicyV2` or `AthleteDecisionContextBuilder`. It serves pre-built audit records.
4. **No On-Demand Execution via HTTP Request:** The HTTP route layer does NOT invoke `DecisionPolicyV2` or `AthleteDecisionContextBuilder`. It serves pre-built audit records.
5. **No Legacy WorkoutBuilder Rewiring:** `DecisionPolicyV2` operates in parallel to the legacy `DecisionEngine`. Legacy `WorkoutBuilder` and workout prescription workflows are untouched.
6. **No Direct Training Plan Mutation:** Recommendation plans provide actionable recommendations (`proceed`, `reduce`, `replace_with_recovery`, `rest`, `review`) without executing physical workout plan mutations.
7. **No LLMs or Generative AI Text:** Policy evaluation, recommendation mapping, headlines, and explainability summaries are 100% deterministic functions.
8. **No Medical Interpretation or Advice:** Biomarker and decision signals strictly evaluate physiological state metrics for training readiness without offering medical diagnostics.
9. **No Interactive Recommendation Acceptance/Rejection in UI:** The AI Coach view in AthleteWeb presents the decision audit record as a read-only experience.
