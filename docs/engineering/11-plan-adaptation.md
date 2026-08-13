# Stage 29.1 — Adaptive Planning Domain Contract

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
