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
snapshot. The canonical dedicated store is
`data/database/activity_reconciliation.duckdb`, with explicit path injection
and `ACTIVITY_RECONCILIATION_DB_PATH` available for isolated composition.

Sprint 28.4 wires `ProductionReconciliationAdapter` into production
composition while retaining `ReconciliationPolicySkipAdapter` for compatibility.
For runtime target date D, the adapter loads a bounded activity window and
reconciles D - 1 with `finalized=True`; it never finalizes the open current day.
Missing previous-day plan context is a truthful
`reconciliation_plan_unavailable` phase skip. Completed phases publish exactly
one resolvable reconciliation artifact and append only when the semantic input
fingerprint is new.

Activity Calendar reads the latest persisted snapshot per date and exposes it
as the nullable `reconciliation` projection without mutating planned sessions or
activities. The projection preserves existing `planned_sessions`, legacy
`planned_session`, and `activities` contracts, and includes replacement evidence.

## Gate B production certification

Gate B completed successfully on 2026-08-12. The controlled production runtime
`runtime-4752ac5c-8cad-451b-abcc-15c61ccd3c72`, targeting 2026-08-12, exited 0
with status COMPLETED at revision 10. Its reconciliation phase completed with
`reconciliations_created=1` and no warning or failure codes.

The runtime reconciled the previous closed local date, 2026-08-11, and created:

- reconciliation ID:
  `reconciliation:sha256:953b8b7deb06cb85f82a332b8926efed296dbea3dea3db3598892d9d4b40ec07`;
- input fingerprint:
  `sha256:953b8b7deb06cb85f82a332b8926efed296dbea3dea3db3598892d9d4b40ec07`;
- `finalized=true`, policy version `1.0`;
- plan `plan-baseline-2026-08-10-v1`, version 1;
- planned VO2 session of 60 minutes;
- no canonical factual activity input;
- `UNMATCHED_PLANNED` with execution outcome `SKIPPED` and reason
  `planned_session_unmatched`.

Live `GET /api/v1/activity-calendar` returned HTTP 200 for 2026-08-11 and
resolved the same reconciliation ID. It exposed `finalized=true` and the
`UNMATCHED_PLANNED` / `SKIPPED` result truthfully while preserving
`planned_sessions`, legacy `planned_session`, and `activities`; the
`replacement_evidence` contract was present.

The controlled runtime created the canonical dedicated database at
`data/database/activity_reconciliation.duckdb`; it did not exist before Gate B.
The pre-certification backup is
`data/database/backups/stage28-gateb-20260812-173604/`. The existing single cron
scheduler remains unchanged and requires no cutover. The D-1 model was certified
without falsely finalizing the open current day. The Git working tree remained
clean after live certification, and no DuckDB handles remained open.

Sprint 28.4 is completed. Stage 28 is closed at 100%, and Roadmap V2 progress is
15%. Stage 29 is the next roadmap stage and has not been started.
