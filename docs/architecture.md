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

