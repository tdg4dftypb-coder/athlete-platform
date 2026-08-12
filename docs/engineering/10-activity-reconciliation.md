# Activity Reconciliation Contract

Sprint 28.3 introduces the `activity_reconciliation` bounded context. It relates
planned intent to observed physical activity without modifying either source.
`ACTIVITY_RECORDED` is the sole factual activity input; historical
`WORKOUT_COMPLETED` remains a separate legacy post-workout event and is ignored
by the matcher to prevent double counting.

Policy `1.0` filters inputs to the explicit athlete-local date. Naive activity
start timestamps are athlete-local wall time; aware timestamps are converted to
the supplied zone (`Europe/Warsaw` by default). REST sessions are excluded from
matching. Explicit compatibility maps cycling session types to `cycling`, SWIM
to `swim`/`swimming`, and STRENGTH/CROSSFIT to their explicitly named sports.
Unknown values are never guessed.

Automatic matching resolves only isolated one-session/one-activity candidate
components. Multiple compatible sessions or activities remain AMBIGUOUS; input
order, session ID, duration, HR, power, cadence, TSS, and feedback never decide
identity. Match status and execution outcome are distinct. After a unique match,
duration completion is capped at 100%: at least 90% is COMPLETED and less than
90% is PARTIAL. Missing duration retains MATCHED status with
`activity_duration_missing` and no execution outcome.

An unmatched training session becomes SKIPPED only when the caller explicitly
marks the date finalized; otherwise it remains unresolved with
`target_date_not_finalized`. REST is neither COMPLETED nor SKIPPED. A factual
activity with no candidate and no ambiguity is UNPLANNED. REPLACED is emitted
only from valid, one-to-one `ReplacementEvidence`; it is never inferred.

Each immutable result records plan identity/version, policy, local date, zone,
finalization, canonical session IDs, exact activity event/source identities,
matches, outcomes, candidates, reason/warning codes, replacement evidence,
evaluation time, and a deterministic input fingerprint. The DuckDB repository
stores one row per fingerprint: identical inputs are idempotent and changed
activity, plan version, finalization, or replacement evidence appends a new
snapshot. Sprint 28.4 should provision a dedicated
`data/database/activity_reconciliation.duckdb`; Sprint 28.3 uses temporary test
stores only.

Production Runtime still uses `ReconciliationPolicySkipAdapter`. For 28.4, the
recommended bounded operational model is to reconcile the previous closed
Warsaw date during today's existing ProductionDailyRuntime. This preserves one
authoritative scheduler and avoids declaring later current-day sessions skipped
during a morning run. Runtime wiring, public outcome projection, and live-data
certification remain deferred. Stage 28 is open at 86.67%; Roadmap V2 is 13%.
