# Stage 29 — Adaptive Training Plan v2

Status: **CLOSED / 100%**. Production Gate B passed on 2026-08-14. Roadmap V2
progress is **30%**.

## Stage 29.1 — Adaptive Planning Domain Contract

## Purpose and ownership

`plan_adaptation/` is the deterministic domain boundary for evaluating future
plan adaptations and describing a validated proposal before any plan mutation.
It owns adaptation windows, evaluation snapshots, action/reason semantics, and
revision proposals. `training_plan/` continues to own `TrainingPlan` and its
persistence. No repository or runtime dependency crosses this boundary in
Stage 29.1.

The future flow is:

```text
TrainingPlan -> evidence -> PlanAdaptationEvaluation
             -> PlanRevisionProposal -> validation -> TrainingPlan version N+1
```

A semantic change will retain `plan_id` and produce version N+1. A no-change
evaluation will not create a plan version. Stage 29.1 represents this distinction
but neither mutates nor persists a plan.

## Frozen v1 boundaries

- Evidence/context dates cover D-7 through evaluation date D.
- Only future dates D+1 through D+7 are eligible for mutation. D and past dates
  cannot appear in a proposal.
- `SKIPPED` and `PARTIAL` outcomes create no automatic training debt. Missed or
  remaining work is not automatically rescheduled.
- Automatic actions are exactly `KEEP`, `SHORTEN`, `REDUCE_INTENSITY`,
  `DOWNGRADE`, and `SKIP`. There is no `MOVE`, `ADD`, or `DUPLICATE` action.
- Session identity, not date, is the adaptation target. Multiple sessions on the
  same date can therefore receive independent actions.
- Models and exposed collections are immutable. Changes are normalized by
  `(session_date, session_id)`, while fingerprints use the Stage 28
  `sha256:<digest>` representation. `evaluated_at` is audit metadata and is not
  defined as semantic fingerprint input.
- Machine explanations use typed deterministic reason codes. Weekly rhythm and
  protected-session rules remain future policy/context data, not domain constants.

## Stage 29.1 non-goals

This sprint contains no adaptation policy, source-plan comparison, evidence
loading, training-load computation, plan mutation, persistence, API/serialization,
production runtime or scheduler integration, database writes, AI Coach changes,
LLM calls, or automatic plan generation. Proposal validation that requires the
source `PlannedSession` belongs to a later sprint.

## Stage 29.2 — Evidence and Adaptation Context

`AdaptationContextBuilder` deterministically normalizes explicit canonical
inputs into one immutable `AdaptationContext`. It performs no policy evaluation
and cannot emit adaptation actions or revision proposals.

The context contains exactly eight `AdaptationHistoryDay` values for D-7...D
and every canonical `PlannedSession` from the source plan in D+1...D+7.
Historical days preserve zero-or-more planned sessions and the complete
`ReconciliationResult`, including match status, activity references, canonical
execution outcomes, ambiguity, unmatched evidence, and an absent outcome.
Future and historical sessions retain stable `session_id`; same-date ENDURANCE,
SWIM, CrossFit, or other planned sessions remain independent.

Evidence sources are deliberately explicit:

- `TrainingPlan` and `PlannedSession` provide future intent and identity;
- `ReconciliationResult`, `ReconciliationItem`, `MatchStatus`, and
  `ActivityExecutionOutcome` provide Stage 28 execution evidence;
- the existing immutable `AthleteAssessment` transports athlete/recovery state;
- `AdaptationTrainingLoad` transports already-produced recent 7-day load, CTL,
  ATL, and TSB values without calculating them;
- `WeeklyRhythm` and `AdaptationConstraint` provide minimal data contracts for
  multi-slot rhythm, fixed sessions, protected recovery, and availability.

Normal operational absence does not prevent context construction. Missing
reconciliation, assessment, training load, rhythm, or constraints remains
`None`/empty and is accompanied by a typed `AdaptationWarningCode`. Partial,
ambiguous, and non-final reconciliation are also visible. Missing metrics never
become zero. A source plan that does not cover all of D+1...D+7 is structurally
insufficient and fails the build.

The `sha256:<digest>` context fingerprint covers evaluation date, source plan
identity/version, historical intent and reconciliation semantics, future
sessions, training load, assessment, constraints, rhythm, and completeness
warnings. Collections are normalized before hashing. Audit-only `built_at` and
reconciliation audit identity/timestamps/fingerprints are excluded.

`AthleteAssessment.as_of` and its nested assessment `as_of` are likewise audit
snapshot timestamps and are excluded from the fingerprint. Assessment status,
fatigue, reasons, training-assessment status, period, and supporting evidence
remain semantic fingerprint inputs.

The current `TrainingPlan` is sport-agnostic through its normalized string
`session_type`, so Stage 29.2 preserves future RUNNING and same-date BIKE/RUN
sessions exactly as canonical `PlannedSession` values. `PlannedSession` does not
currently define session grouping, sequence, parent, or relationship semantics.
Consequently the context preserves independent multi-session identity but does
not infer whether sessions form a brick or another combined workout. A future
explicit brick/bike-run relationship belongs in the TrainingPlan contract when
that bounded context requires it; Stage 29.2 neither invents nor interprets it.

Stage 29.2 adds no evidence repositories, policy rules, plan mutation,
persistence, API, runtime wiring, scheduler work, or production operations.

## Stage 29.3 — Deterministic Adaptation Policy

`DeterministicAdaptationPolicy` v1.0 maps one immutable `AdaptationContext` to
one immutable `PlanAdaptationEvaluation`. It has no repository, clock, random
identity, I/O, or global state. `evaluated_at` is explicit audit metadata;
`adaptation_id` is derived from policy version and the context fingerprint.
The evaluation retains `context.input_fingerprint` unchanged and propagates
context completeness warnings without turning them into adverse reasons.

The default is to preserve the plan. Policy v1 has one narrow safety rule:

```text
AthleteAssessment CAUTION
+ explicit LOW_RECOVERY or HIGH_FATIGUE canonical signal
-> SHORTEN the nearest eligible future TRAINING session to 70% duration
-> recovery_protection
```

The shared `training_plan.reduction.DURATION_REDUCTION_FACTOR_V1` owns the 0.70
duration-reduction contract. `DailyTrainingReconciler.REDUCTION_FACTOR` remains
a compatibility alias and both daily reconciliation and Stage 29.3 consume the
neutral contract; `plan_adaptation` does not depend on the application service.
Stage 29.3 introduces no new load or biomarker threshold. Source-aware
validation requires the target duration to be positive and strictly shorter;
an unshortenable one-minute session is ignored. REST is skipped during
selection.

Target selection is semantic: choose the nearest date with legally shortenable
TRAINING sessions, then the unique lowest numeric `PlannedSession.priority`
(priority 1 is least important and priority 5 most important). `session_id`
remains identity and canonical ordering, never training priority. If multiple
same-date candidates share the lowest priority, policy v1 emits no change and
adds `AMBIGUOUS_ADAPTATION_TARGET`; it does not choose arbitrarily by ID. Thus
at most one session changes and the full week is never rewritten.

Semantic precedence remains safety/recovery, explicit constraints, excess
stress, protected recovery, actual performed load, weekly structure, then plan
preservation. Only the safety rule is implemented in v1, so no competing action
rules exist yet. Future conflicts must emit at most one action per `session_id`,
use protective precedence (`SKIP > DOWNGRADE > REDUCE_INTENSITY > SHORTEN`), and
retain all applicable typed reasons when those actions have safe source-aware
targets.

COMPLETED preserves the plan. PARTIAL, SKIPPED, REPLACED, and UNPLANNED alone
also preserve it: they do not create training debt, make-up work, load guesses,
or new sessions. Missing assessment is not adverse evidence. Missing load does
not block an independent assessment safety signal, but policy v1 does not
interpret recent load, CTL, ATL, or TSB because the repository has no canonical
threshold contract for them.

Policy v1 emits `SHORTEN` only. It deliberately does not emit
`REDUCE_INTENSITY` because intensity is an unordered string, `DOWNGRADE` because
there is no canonical session-type mapping, or `SKIP` because the existing
assessment semantics support reduction rather than automatic cancellation.
It never emits KEEP entries, MOVE, ADD, DUPLICATE, or sport conversion.

Open session types such as RUNNING remain supported without a whitelist.
CrossFit and every other planned training type are treated as ordinary source
sessions; no discipline-specific fatigue heuristic is applied. Same-date BIKE
and RUN sessions remain independent because TrainingPlan still has no brick or
grouping semantics.

Stage 29.3 stops at `PlanAdaptationEvaluation`. Proposal construction,
cross-check validation, TrainingPlan version N+1, persistence, and runtime
integration belong to Stage 29.4 or later.

## Stage 29.4 — Proposal Validation and Plan Versioning

`PlanRevisionProposalBuilder` maps `NO_CHANGE` to `None` and maps
`CHANGE_PROPOSED` to an immutable `PlanRevisionProposal`. Callers cannot replace
semantic evaluation fields. Proposal identity is `proposal:sha256:<digest>` over
policy version, evaluation date, source plan identity/version, windows, changes,
reasons, warnings, and evidence fingerprint. The explicit evaluation audit time
is preserved but excluded from identity.

`PlanRevisionValidator` validates the entire proposal against one concrete
source `TrainingPlan` before materialization. Typed failure codes distinguish
wrong plan identity, stale or future source version, unknown session identity,
date mismatch, outside-window targets, illegal source kind, non-reduction,
unsupported actions, and no semantic change. A proposal for version N cannot be
applied to N+1. Validation and materialization are side-effect free and atomic:
one invalid change rejects the whole proposal.

Stage 29.4 materializes only `SHORTEN`. The source must be TRAINING and the
target must satisfy `0 < target < source duration` and equal the canonical v1
duration reduction. The shared helper retains established truncation semantics,
for example 60 -> 42 and 90 -> 62. The latter is intentionally compatibility
behavior: binary floating-point represents `90 * 0.70` just below 63 and the
historical contract applies `int(...)` truncation. Existing Stage 26 tests
explicitly certify 90 -> 62, so Stage 29.4 does not silently change it. A
one-minute session cannot be shortened.
The session retains `session_id`, date, kind, type, intensity, priority, and
rationale. `target_tss`, when present, is proportionally reduced by the same
shared 0.70 contract already used by daily reconciliation; missing TSS remains
missing and zero remains `0.0`. The factor is prescription-reduction semantics,
not the ratio of integer-materialized minutes: therefore 90 -> 62 minutes and
100 -> 70 TSS are canonical together. Invalid boolean, negative, NaN, and
infinite TSS inputs are rejected by the shared primitive. This avoids a
shortened session retaining an unreduced load target and does not introduce a
new TSS formula.

The validator remains policy-agnostic about *why* a reduction is requested, but
Stage 29.4 materialization v1 supports only the shared 0.70 reduction contract.
Thus policy chooses whether and which session to shorten; the revision layer
checks general source legality plus whether the requested target is supported by
the currently available materializer. Arbitrary shorter targets remain valid at
the Stage 29.1 shape level but are rejected as unsupported materialization until
a canonical target-TSS semantic for arbitrary durations exists.

`REDUCE_INTENSITY` is rejected because intensity remains an unordered string.
`DOWNGRADE` is rejected because there is no canonical session-type mapping.
`SKIP` is rejected because TrainingPlan has no canonical skip materialization
that safely preserves coverage and multi-session semantics. `KEEP` is not a
semantic mutation and cannot independently produce a proposal or version.

`TrainingPlanRevisionService` validates first, constructs candidate sessions in
memory, verifies a real session-level semantic diff, and returns the same
`plan_id` with `version = source.version + 1`. Date range, supersession metadata,
untouched sessions, and all stable session identities are preserved. The new
`generated_at` is explicit audit input and cannot determine legality. Same-date
siblings and open types such as RUNNING remain independent; no sport conversion
or brick relationship is inferred.

The certified in-memory vertical slice is context -> deterministic policy ->
evaluation -> proposal -> validated TrainingPlan N+1. Healthy context follows
NO_CHANGE -> no proposal -> no new version. Stage 29.4 adds no persistence,
repository, DuckDB, API, or production runtime integration; those boundaries
remain Stage 29.5 or later.

## Stage 29.5 — Persistence, History and Read Contracts

Plan-adaptation audit is append-only in the dedicated
`plan_adaptation.duckdb`, resolved by `PLAN_ADAPTATION_DB_PATH` or an explicit
path. Its three tables store immutable evaluations, proposals linked to
`adaptation_id`, and revision records linked to both proposal and evaluation.
Payloads use schema version 1.0 and lossless canonical JSON; unknown enum or
schema values fail decoding rather than becoming defaults.

`PlanRevisionRecord` represents `APPLIED` with a result plan reference or
`REJECTED` with a typed Stage 29.4 failure code. NO_CHANGE is stored as an
evaluation only: it creates neither proposal, revision record, nor plan version.
Revision IDs are deterministic over proposal and applied/rejected semantics;
audit timestamps do not define identity or collision semantics. A retry with the
same semantic evaluation/proposal/revision and a different `evaluated_at` or
`applied_at` returns `False` and preserves the timestamp of the first append.
Semantic fields such as changes, source version, status, result reference, or
failure code still participate in collision comparison; changing one under the
same ID raises a hard collision.

TrainingPlan remains canonically owned by `training_plan`. Existing base-plan
`save()` semantics and the legacy `training_plans` table are unchanged. The
same repository owns an append-only `training_plan_revisions` table and exposes
`append_revision(expected_source_version=N, plan=N+1)`. It accepts an identical
retry, rejects a different competing N+1, and requires the persisted latest
version to remain N. Both N and N+1 remain addressable by `(plan_id, version)`;
latest and history reads include revisions.
Together the base and revision tables form one logical `(plan_id, version)`
stream. Exact-version lookup and duplicate checks query both physical stores;
an identical tuple across either table is an idempotent existing record and a
different payload is a conflict. `get_by_id(plan_id)` now means the latest
logical version, matching provider/latest-plan usage, while
`get_by_id_version` is the explicit historical read.

`AdaptationPersistenceCoordinator` persists precomputed artifacts only. For an
applied result it writes evaluation, proposal, canonical plan N+1, verifies the
exact result reference is readable, then writes APPLIED. Rejected attempts write
evaluation, proposal, and typed REJECTED without a result plan. There is no
cross-database ACID claim. Deterministic IDs, collision checks, ordered writes,
and idempotent retry allow recovery from a plan-written/audit-missing partial
state without creating N+2. An APPLIED row is never emitted before its canonical
result plan resolves.

Read contracts include evaluation/proposal/revision by ID, revision by
adaptation, global latest evaluation, latest for local evaluation date,
chronological evaluation history, and a consistent `AdaptationHistoryEntry`.
Ordering is `(evaluation_date, evaluated_at, adaptation_id)` with the reverse
ordering for latest. The read aggregate rejects NO_CHANGE with proposal/revision
and revision without proposal. No HTTP, policy execution, context loading,
production runtime, or scheduler integration is included; those remain Stage
29.6 or later.

A persisted CHANGE_PROPOSED evaluation plus proposal and no revision is a
truthful partial-write/unprocessed state, not APPLIED or REJECTED. The
cross-store `AdaptationHistoryReader` additionally verifies every APPLIED result
reference against canonical TrainingPlan persistence and raises explicit data
corruption when it cannot resolve; raw audit records never manufacture a result.
REJECTED retains only a typed validation failure and never catches programmer,
database, or unexpected exceptions as normal domain rejection.

## Stage 29.6 — Production Runtime Integration

The authoritative daily runtime now contains `plan_adaptation` immediately
after `plan_prescription` and before `morning_briefing`. It consumes the latest
logical TrainingPlan, the already persisted attempt-bound assessment snapshot,
latest reconciliation results for D-7...D, and the snapshot's canonical recent
training load. Constraint and weekly-rhythm providers are not yet canonical in
production composition, so both are passed as unavailable and remain explicit
warnings. No raw biomarker rule or new threshold is introduced.

The phase targets D+1...D+7 only. A plan without that complete future horizon
returns `SKIPPED`, `changed_state=false`, and
`adaptation_insufficient_plan_horizon`; it neither extends nor replaces the
plan. NO_CHANGE persists exactly one evaluation and completes unchanged.
CHANGE_PROPOSED persists evaluation and proposal, validates and materializes
N+1, appends the canonical plan revision, verifies it is resolvable, and then
persists APPLIED. Typed proposal validation writes REJECTED and completes with
`changed_state=false`; storage conflicts, missing required artifacts, and
unresolvable APPLIED history fail the runtime phase.

Runtime artifacts list deterministic evaluation, proposal, revision-record,
and (for APPLIED) result-plan references. Publication remains after morning
briefing and runtime completion requires the new phase for new attempts. Older
audit payloads remain readable because phase tuples are decoded as recorded;
the stricter completeness invariant applies only while executing a current
attempt, not when reading historical terminal records.

Retry/cascade protection uses a small append-only runtime guard in the
adaptation audit database. Its policy-trigger key hashes the local evaluation
date, policy version, and only AthleteAssessment fields interpreted by policy
v1: status, fatigue status, and LOW_RECOVERY/HIGH_FATIGUE reasons. Audit time,
runtime ID, plan version, training load, and reconciliation are deliberately
excluded. The complete AdaptationContext fingerprint still includes all
canonical evidence, but a reconciliation-only/context-only change cannot reset
an unchanged recovery-protection trigger.

Before applying a genuinely changed same-day trigger, runtime also checks
APPLIED history by evaluation date, policy version, stable session ID, and
action. The same session cannot receive the same SHORTEN protection twice on
one evaluation date, while a different session remains eligible. The guard is
date-scoped, so the next day may legally adapt a different future session.

The guard is written after the deterministic evaluation and before proposal or
plan writes. It is resolved before context reconstruction or policy evaluation.
Resume reconstructs a missing deterministic proposal, completes a
missing plan revision, or recognizes an already persisted matching N+1 and
finishes its APPLIED record. Existing NO_CHANGE and REJECTED outcomes are
returned without duplication. A mismatching competing N+1, stale/missing source,
guard without evaluation, or unresolvable APPLIED reference is corruption or a
conflict and fails rather than being guessed around.

Production composition injects the TrainingPlan repository, reconciliation
repository, attempt snapshot repository, dedicated adaptation audit repository,
runtime clock, context builder, deterministic policy, proposal builder,
revision service, persistence coordinator, and history reader. Open session
types including RUNNING pass unchanged; stable session IDs and the policy's
canonical priority selection retain multi-session behavior, and no brick
relationship is inferred.

The adaptation DuckDB repository initializes lazily. Importing modules,
resolving the canonical path, read-only preflight inspection, and constructing
the production resource graph do not create `plan_adaptation.duckdb`; schema
creation begins only when the adaptation phase accesses its store.

Stage 29.6 changes neither scheduler cadence nor the runtime entrypoint. It adds
no HTTP endpoint and performs no Gate B/live run. Production activation and
later adaptive-planning capabilities remain outside this sprint and Stage 29.7.

## Stage 29.7A — Horizon Continuity Contract Foundation (Gate A, completed)

Routine horizon continuity is not a new logical training plan. It appends only
future dates to the latest immutable version of the same plan:

```text
plan-A vN -> plan-A vN+1
same plan_id, start_date, supersedes_plan_id
extended end_date, existing sessions unchanged
```

`TrainingPlanContinuationSpecification` is canonical training-plan-owned
configuration persisted in `training_plan.duckdb`. It has an ID/version,
target plan ID, explicit `target_horizon_days` and `extension_days`, seven weekday definitions, semantic
fingerprint, and audit creation time. Each weekday is exactly one REST slot or
one-or-more TRAINING slots. Stable `slot_id` permits multi-session days and
open normalized session types without brick inference. Generated identity is
`{plan_id}:{spec-version}:{date}:{slot_id}`; timestamps do not participate.

Adaptation and continuity horizons are intentionally distinct. Adaptation still
mutates only D+1...D+7. Continuity is proactive capacity maintenance: it checks
`D + target_horizon_days` and advances by the minimum number of complete
`extension_days` chunks that covers that configured target. The two configured
values need not be equal. It copies
all existing sessions byte-for-domain-semantics, including earlier adaptive
reductions, and generates only dates after the previous end. Persistence uses
the existing `append_revision(expected_source_version=N)` optimistic-concurrency
contract: identical N+1 is idempotent and a different competing N+1 fails.

The authoritative order is prescription, `plan_horizon_continuity`, plan
adaptation, briefing, publication. Successful extension is read back before
publishing `training-plan:{plan_id}:v{version}`. A crash after plan write is
recovered because the next attempt resolves sufficient coverage and the exact
latest version; it does not create N+2. Missing specification is an
operator-visible failed phase, not inferred from historical sessions.

For the plan ending 2026-09-06, a configured 28-day target and 28-day chunk
already require proactive extension at D=2026-08-13 (target 2026-09-10) and
D=2026-08-14 (target 2026-09-11), producing the same plan ID at N+1 ending
2026-10-04. One canonical
source plan then covers the complete 2026-09-03...09-09 adaptation window, so
no composite view or multi-plan transaction is introduced. Adaptation consumes
N+1 and may independently produce N+2.

An explicit logical-intent transition `plan-A -> plan-B` remains outside v1.
Continuity refuses a specification for a different plan ID and never joins two
logical plans into one context. The operator-only continuation import is
dry-run-first and consumes a native `schema_version=1.0` JSON contract containing
plan/specification identity, independent target and extension horizons, UTC
audit time, exactly seven weekday definitions, and every explicit training
`slot_id`. A REST weekday has no `slots`; a TRAINING weekday has one-or-more
slots and therefore supports multi-session days without an arbitrary limit.
Session types remain open and normalized by the domain. The input is the single
source of semantic truth: the CLI accepts only `--input`, optional
`--training-plan-db`, and explicit `--apply`, with no metadata overrides. It
prints the canonical fingerprint plus a seven-day/slot preview and never infers
private weekly intent from persisted sessions.

Dry-run performs validation only and cannot open or create the target database.
Apply registers only the continuation specification: it neither extends a plan
nor runs adaptation/runtime. Reapplying identical semantics is a no-op even if
`created_at` differs; the same specification ID/version with changed semantics
is a hard conflict. The repository contains only the synthetic format example
`docs/examples/training-plan-continuation.example.json`, not production intent.

Phase A performed only temporary-database automated certification. Registration
of the real specification, backups, controlled runtime, and post-run read-only
certification were completed by Gate B without changing scheduler cadence.

## Stage 29.7B — Production Gate B and closure

Production Gate B **PASSED** on 2026-08-14. The operator-controlled continuation
specification was persisted with `target_horizon_days=28` and
`extension_days=28`. The accepted production baseline was
`plan-baseline-2026-08-10-v1` v2 ending 2026-09-06, including the canonical
APPLIED adaptation for the 2026-08-15 SST session from 75 to 52 minutes.

The controlled runtime extended the same logical plan from v2 to v3, ending
2026-10-04. `PLAN_HORIZON_CONTINUITY` completed with `changed_state=True`.
`PLAN_ADAPTATION` completed with `changed_state=False`; its same-day guard
prevented a second SHORTEN and preserved the 52-minute SST session. Morning
briefing, publication, and the overall runtime completed. The certified backup
reference is `data/database/backups/stage29-gateb-20260814-093955`; database and
manifest artifacts remain outside Git.

The final production flow is:

```text
REAL DATA
-> FACTS
-> ATHLETE STATE
-> DECISION
-> PLAN
-> HORIZON CONTINUITY
-> ADAPTATION
-> MORNING BRIEFING
-> PUBLICATION
-> EXECUTION
-> OUTCOME
-> LEARNING
```

Routine continuity proactively maintains its configurable target horizon by
versioning one logical plan: `plan-A vN -> plan-A vN+1`. It does not implement
`plan-A -> plan-B`. The production target horizon and extension chunk are both
28 days, while adaptation retains its separate D+1...D+7 mutation horizon.
These horizons have distinct semantics and must not be conflated.

Final v1 limitations remain explicit:

- routine continuity does not support an explicit logical transition from
  `plan-A` to `plan-B`;
- brick/grouping semantics are not modeled;
- session types remain open;
- adaptation v1 actively emits `SHORTEN` under the existing deterministic
  policy and adds no new policy actions;
- the continuation specification is operator-controlled persisted intent.

Stage 29 is **CLOSED at 100%**. Stage 30 has not been started.
