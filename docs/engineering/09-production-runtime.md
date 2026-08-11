# Production Runtime and Reliability Contract

Status: Stage 27.2 operational contract and audit persistence, 2026-08-11.
Stage 27.1 established the baseline topology; Stage 27.2 implements the
foundation described below. The production coordinator remains unimplemented.

## Conclusion and current topology

There is no authoritative end-to-end production runtime. The scheduled
`python -m scripts.run_daily_decision_runtime` is authoritative only for the
Decision Intelligence plus Final Session Prescription slice. It assumes that
input stores are current and a persisted Training Plan already covers the day.
FIT/health ingestion, canonical fact synchronization, plan creation, and
read-model delivery are separate. Morning Briefing is rebuilt on demand and is
not a persisted daily artifact.

```text
FIT -> scripts.imports.import_workouts
       -> health.duckdb.workouts + ACTIVITY_RECORDED
    -> scripts.import_completed_fit -> WORKOUT_COMPLETED (non-production DB only)
    -> scripts.backfill_activity_facts -> ACTIVITY_RECORDED

health.duckdb -> MorningCoachUseCase
  -> health/recovery/performance -> memory review -> assessments
  -> legacy intelligence/planner/dashboard
  -> ProductionMorningBriefingInputProvider <- biomarkers.duckdb
       -> Decision Intelligence 2.0

training_plan.duckdb (pre-existing plan)
  -> TrainingPlanDecisionContextAdapter
  -> DailyDecisionRuntimeCoordinator
       -> decisions.duckdb ledger + DecisionAuditRecord
  -> AdaptiveDailyRuntimeCoordinator
       -> training_plan.duckdb FinalSessionPrescription

WSGI server independently reads all stores and builds APIs/read models on demand.
```

`MorningCoachUseCase` already coordinates health, recovery, training load,
weekly memory review, knowledge/training/athlete assessment, adaptation, legacy
intelligence, planning, reporting, and the legacy dashboard. Decision
Intelligence 2.0 consumes a projection of that result plus biomarkers. The
Stage 26 coordinator persists one daily-ledger Decision and a deterministic
prescription; it does not ingest or materialize a briefing.

## Entrypoints and legacy classification

| Entrypoint/composition | Capability | Classification |
|---|---|---|
| `scripts.run_daily_decision_runtime` / `create_production_adaptive_daily_runtime` | Ledger, Decision 2.0, reconciliation/prescription | KEEP, then MIGRATE behind Stage 27 coordinator |
| `decision.daily_production_composition` | Stage 25 decision-only daily composition | DEPRECATE; overlapped by Stage 26 composition |
| `scripts.run_decision_runtime` / `decision.production_composition` | Uncoordinated persisted Decision | DEPRECATE; every call can create another same-day decision |
| `scripts.imports.import_workouts` | Standard FIT analysed facts and canonical event sync | KEEP, then MIGRATE to ingestion phase; machine-specific source default |
| `scripts.backfill_activity_facts` | Date-bounded legacy-to-canonical projection | KEEP as dry-run-first maintenance/recovery |
| `scripts.import_completed_fit` | One FIT reconciled with catalog workout, writes legacy event | REVIEW; refuses production DB and omits `ACTIVITY_RECORDED` |
| health/sleep import/build scripts | Apple Health import and derived tables | REVIEW, then MIGRATE to bounded adapter |
| `scripts.import_laboratory_pdf` | Biomarker ingestion | KEEP as optional source command |
| plan builder plus plan repository | Build/persist Training Plans | REVIEW; no production application/CLI creates the required plan |
| `server.app.create_production_dashboard_wsgi_app` | Production APIs/read models | KEEP, then MIGRATE shared composition; remain read-only |
| `scripts.export_live_dashboard` | Static legacy dashboard JSON | DEPRECATE |
| `scripts.morning_coach` | Canonical use-case console report | KEEP as diagnostic |
| `scripts.morning_briefing`, `scripts.morning` | Old direct briefing/FIT flows | DEPRECATE; bypass production provider, one has absolute Zwift path |
| `application.composition` | Morning Coach service composition | KEEP |
| repeated adaptive/decision/server production wiring | Health, biomarker, briefing, repository construction | MIGRATE to one owned resource graph |
| macOS LaunchAgent tooling | Schedules current daily CLI | KEEP; switch command only after migration |

Demo, debug, reset, report, bootstrap, and export scripts are not daily
production entrypoints. Maintenance reset operations must never be coordinator
phases.

## Persistence and DuckDB locking

| Store | Contents/current users | Default | Risks |
|---|---|---|---|
| Health | health/sleep, legacy `workouts`, Athlete Memory; ingestion, Morning Coach, Calendar | `data/database/health.duckdb` | Highest contention: writers versus long-lived server/runtime readers. `PerformanceEngine` opens a hidden default DB via `WorkoutHistoryBuilder`, so injected non-default paths do not fully isolate composition. |
| Biomarkers | laboratory persistence/dashboard | `data/database/biomarkers.duckdb` | Import can conflict with readers. Provider failure currently aborts Decision even though source is conceptually optional. |
| Decisions | audit records and daily ledger | `data/database/decisions.duckdb` | Adaptive composition shares a connection but repositories have separate Python locks. CAS handles logical races, not DuckDB file locks. No transient-lock retry/backoff. Legacy repository default remains `decision_intelligence.duckdb`, overridden by production path helper. |
| Training Plan | plans and prescriptions | `data/database/training_plan.duckdb` | Short-lived connections and instance-local locks; multiple instances/processes can contend. IDs and natural keys prevent duplicate identical records. |

Decision and Training Plan defaults are anchored at repository root. Health and
biomarker defaults are working-directory-relative, so direct callers may open a
different file; the LaunchAgent avoids this only by setting `WorkingDirectory`.
Resource ownership is also unclear: the inner Decision container closes shared
health/biomarker resources while the outer adaptive container has different
lifecycle rules.

## Ordering, idempotency, and duplicate risks

Target ordering:

1. ingest and synchronize canonical facts;
2. freeze target local date and source watermarks;
3. reconcile completed work against persisted plan state;
4. build the assessment snapshot;
5. create/recover the target-day Decision;
6. select/create applicable plan and persist final prescription;
7. materialize Morning Briefing from that snapshot;
8. publish read-model availability and complete the runtime audit.

Current Stage 26 requires a plan before reserving the Decision and reconciles
only that planned session with the Decision. It does not reconcile newly
completed activity into future plan state.

Current guarantees:

- standard FIT facts use file-name existence/replacement;
- events are unique per `(event_type, source_type, source_key)`; Activity Calendar
  prefers canonical `ACTIVITY_RECORDED` over `WORKOUT_COMPLETED` for one source;
- backfill is idempotent and dry-run by default;
- plans, Decisions, and prescriptions no-op for identical IDs/payloads and
  reject conflicting payloads;
- the daily ledger is at-most-once per Warsaw local date, with a 15-minute
  lease, CAS, stable reserved Decision ID, and audit-record crash recovery;
- prescription ID `{planned_session_id}:{decision_id}` makes repair after a
  completed Decision idempotent.

Duplicate or divergence risks:

- `run_decision_runtime` bypasses the ledger and creates fresh IDs;
- changed/copied FIT artifacts can evade artifact-based source identity;
- legacy and canonical event types coexist; every consumer must apply a
  consistent preference policy;
- overlapping plans with different IDs are allowed; newest wins;
- briefing/dashboard calls can differ without an audit record;
- raw workout insertion and canonical event append are separate writes, though
  a retry normally repairs the latter.

## Time and snapshot semantics

- The daily coordinator records aware UTC timestamps and derives Warsaw date;
  ledger timestamps are stored naive UTC and restored aware.
- plan/prescription indexed timestamps normalize to naive UTC; selection and
  Activity Calendar accept explicit dates.
- Calendar treats naive FIT timestamps as Warsaw wall time, but historical
  backfill labels legacy naive timestamps UTC. Near-midnight dates can differ.
- Morning Coach uses the last health-history day with sleep, not wall-clock
  today.
- the production briefing provider stamps UTC now, compares source date against
  the UTC date (not Warsaw date), and accepts no target date.
- Decision generated time is converted to Warsaw for plan lookup. The general
  context calls the briefing provider, and the training adapter may call it
  again for load/fatigue, so the Decision can span two logical snapshots.
- HTTP briefing/dashboard are recomputed; persisted latest/history endpoints
  read independently. There is no multi-store snapshot token.

Near Warsaw midnight a ledger may reserve day D while freshness is evaluated
as UTC day D-1 and health “today” is older. Stage 27 should freeze
`target_local_date`, `started_at_utc`, and input watermarks once. Historical
naive timestamp semantics need a separate migration decision.

## Failure and recovery matrix

| Scenario | Current result | Assessment |
|---|---|---|
| No new activity | Runtime does no ingestion and decides from current stores | Cannot prove synchronization |
| New FIT available | Ignored until separate import | Decision may use stale load/memory |
| Already imported | Standard import/event writer skips | Safe for same artifact identity |
| No Training Plan | `MISSING_PLAN` before ledger reservation | Retryable, but no persisted run failure |
| Existing plan | Newest applicable plan, provenance in Decision | Safe subject to overlap policy |
| Decision already generated | Ledger path reuses it and repairs prescription | Safe only through coordinated path |
| Executed twice | Decision skip plus prescription lookup/repair | Safe for current slice only |
| Stops after Decision | Ledger may be `COMPLETED`; next run repairs prescription; briefing is recomputed | Ledger overstates whole-day completion |
| DB locked | Usually `FAILED`, often with detail suppressed; later invocation may retry | No typed transient failure/backoff/phase audit |
| Optional source unavailable | performance defaults unavailable; biomarker failure aborts main context | Optionality inconsistent |

Across four databases there is no atomic snapshot/commit. Recovery should use
phase idempotency and a persisted phase ledger, not distributed transactions.

## Proposed target architecture

```text
ProductionDailyRuntime (thin application coordinator)
  -> ActivityIngestionSynchronizer
  -> CompletedTrainingReconciliationService
  -> AthleteAssessmentSnapshotService
  -> DailyDecisionRuntimeCoordinator (existing)
  -> TrainingPlan/Prescription application service
  -> MorningBriefingSnapshotService
  -> RuntimeAuditRepository
```

One composition root resolves canonical paths, owns resources, and injects a
clock and explicit target date. Each existing service returns a bounded
operational phase result. The server stays read-only and must not run workflows
as a side effect of GET.

## Implemented immutable runtime result/audit contract (27.2)

```python
@dataclass(frozen=True)
class ProductionDailyRuntimeResult:
    runtime_id: str                       # new operational ID, not domain ID
    logical_execution_key: str            # target date + contract version
    revision: int
    contract_version: str
    target_local_date: date
    timezone_name: str
    started_at_utc: datetime
    completed_at_utc: datetime | None
    status: RuntimeStatus                 # running/completed/partial/failed
    phases: tuple[RuntimePhaseResult, ...]
    decision_id: str | None
    training_plan_id: str | None
    prescription_id: str | None
    morning_briefing_available: bool
    activities_discovered: int | None
    activity_facts_created: int | None
    activities_already_present: int | None
    reconciliations_created: int | None
    source_watermarks: tuple[SourceWatermark, ...]
    warnings: tuple[RuntimeWarning, ...]
    failure: RuntimeFailure | None

@dataclass(frozen=True)
class RuntimePhaseResult:
    phase: RuntimePhase
    status: PhaseStatus                   # completed/skipped/failed
    started_at_utc: datetime
    completed_at_utc: datetime
    changed_state: bool
    item_count: int | None
    artifact_ids: tuple[str, ...]
    warning_codes: tuple[str, ...]
```

The implementation lives in the dedicated `production_runtime/` bounded
package and uses contract version `1.0`. The final model represents failure as
a nested `RuntimeFailure(code, phase, detail)` rather than two loosely coupled
fields. Warnings similarly use stable codes with optional bounded detail and
source. `SourceWatermark(source, kind, value, observed_at_utc)` intentionally
keeps watermark kind and value generic; future adapters report only real source
boundaries.

One unique `runtime_id` identifies one physical execution attempt. The stable
`logical_execution_key` is `<target-local-date>:<contract-version>` and groups
multiple attempts without replacing them. It is not a Decision, plan, or
prescription ID. Every persisted lifecycle snapshot also has a monotonically
increasing `revision` scoped to the runtime attempt.

Runtime lifecycle semantics are:

- `RUNNING`: an attempt has been durably started; it has no completion time or
  failure;
- `COMPLETED`: every required future phase has completed or been explicitly
  skipped under coordinator policy; it has no failed phase or failure record;
- `PARTIAL`: the attempt stopped after producing some valid operational state,
  but did not satisfy whole-runtime completion;
- `FAILED`: the attempt terminated unsuccessfully and has a stable operational
  failure code. Raw tracebacks are not part of the contract.

Canonical persisted phase values are `ingestion`,
`activity_fact_synchronization`, `reconciliation`, `assessment`, `decision`,
`plan_prescription`, `morning_briefing`, and `publication`. Phase results are
terminal `completed`, `skipped`, or `failed` records with aware UTC boundaries,
a state-change flag, optional count, artifact IDs, and warning codes. Phase
execution is not implemented in 27.2.

All public timestamps must be timezone-aware UTC. `RuntimeClock` and
`SystemUtcRuntimeClock` provide the small clock boundary. `target_local_date_at`
derives Warsaw local date once at the future coordinator boundary; the target
date remains an explicit model field and can differ from the current date for a
retry or historical run. No repository derives dates or calls `datetime.now()`.

Completion retains the Stage 27.1 meaning: all required phases completed or
policy-skipped, referenced artifacts resolve when applicable, and Morning
Briefing is available for the same snapshot. Existing
`daily_decision_executions.COMPLETED` proves only the Decision phase.

## Runtime audit persistence (27.2)

Runtime audit uses a dedicated operational database,
`data/database/production_runtime.duckdb`, resolved relative to repository root
or overridden by `RUNTIME_AUDIT_DB_PATH`. This is intentionally separate from
health, biomarker, Decision, and Training Plan ownership: audit lifecycle and
lock contention should not be coupled to any one domain store. It is an
additional operational store, not database consolidation.

`RuntimeAuditRepository` supports append, latest revision by `runtime_id`, all
latest attempts for a target date, and deterministic latest-attempt lookup.
`DuckDbRuntimeAuditRepository` stores immutable revisions in
`production_runtime_audit_revisions` with primary key
`(runtime_id, revision)`. An initial attempt must be revision 1. Later revisions
require the exact expected prior revision. Re-appending an identical revision is
an idempotent no-op; a different payload conflicts. Identity fields and existing
phase results cannot change, and terminal attempts cannot transition. This
append-only revision model is the smallest persistence design that can record
`RUNNING` before work, preserve attempt history, and later support recovery
without arbitrary mutable rows.

The JSON codec and indexed metadata use schema version `1.0`, distinct from the
runtime contract version even though both currently have the same value. This
is a fresh table/database, so no synthetic migration framework was introduced.
Minimal production composition constructs only the audit repository; it does
not construct or call a runtime coordinator.

## Stage 27 migration plan

1. Sprint 27.2: completed — immutable operational models/enums, append-only
   audit revisions, dedicated DuckDB adapter/path, clock/date boundary, codec,
   minimal composition, and contract/persistence tests.
2. Sprint 27.3: extract shared path/resource composition; wrap standard FIT
   discovery/import and canonical synchronization as an idempotent phase. Keep
   historical backfill separate.
3. Sprint 27.4: compose assessment, existing daily Decision, prescription, and
   persisted or snapshot-addressable Briefing; add resume and typed optional/
   transient outcomes.
4. Sprint 27.5: switch CLI, then LaunchAgent; expose read-only run status and
   retain deprecated commands for one warning/migration window.
5. Delete duplicate/legacy paths only after call-site, operations, and data
   migration verification.

Do not yet tackle cross-provider semantic deduplication, reinterpret historical
timestamps, change coaching or plan-generation policy, consolidate databases,
add distributed transactions, redesign scheduling, delete legacy events, or add
conversational AI.

## Executable evidence

Key coverage lives in `tests/decision/test_daily_coordinator.py`,
`tests/application/test_adaptive_daily_runtime.py`,
`tests/scripts/test_run_daily_decision_runtime.py`, FIT/backfill and
`tests/activity_calendar/`, `tests/morning_briefing/test_production_provider.py`,
server production-composition tests, and `tests/training_plan/`.
