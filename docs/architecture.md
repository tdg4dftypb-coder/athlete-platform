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
| `MorningBriefing` | Distinct models in `briefing.models` and `core.results`. |
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
