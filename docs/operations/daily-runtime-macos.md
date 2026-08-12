# Operations Manual — macOS Production Daily Runtime Cutover

Sprint 27.7 Gate B passed on 2026-08-12. LaunchAgent remains the preferred macOS
backend. User cron is the supported fallback when managed-host permissions make
`~/Library/LaunchAgents` unavailable. Exactly one backend may be active.
LaunchAgent uses 07:00 local time with `RunAtLoad=true`; cron uses a preferred
07:00 invocation plus hourly same-day catch-up through 23:00. Both use the
repository environment and logs under `~/Library/Logs/AthletePlatform`.

After cutover the only scheduled command is:

```bash
.venv/bin/python -m scripts.run_production_daily_runtime --scheduled
```

The legacy `python -m scripts.run_daily_decision_runtime` remains rollback-only.
Never schedule both commands.

## PRE-FLIGHT

From the repository root:

```bash
.venv/bin/python -m scripts.production_runtime_preflight
.venv/bin/python -m scripts.runtime_status --date "$(TZ=Europe/Warsaw date +%F)"
./ops/macos/install_daily_runtime_launchagent.sh --dry-run
./ops/macos/install_daily_runtime_cron.sh --dry-run
```

Supply explicit path options to preflight when production uses overrides. It is
read-only and checks interpreter, working directory, FIT source, all stores, an
applicable plan, runtime-audit readability/parent writability, and command
resolution. Any FAIL blocks cutover.

Inspect holders non-destructively:

```bash
lsof data/database/health.duckdb data/database/biomarkers.duckdb \
  data/database/decisions.duckdb data/database/training_plan.duckdb \
  data/database/production_runtime.duckdb
```

Manually close a conflicting writer/server. Never kill automatically, delete
locks, or stop the WSGI server from tooling.

## INITIAL TRAINING PLAN BOOTSTRAP

This is an explicit one-time prerequisite only when preflight reports no
applicable persisted Training Plan. It is not automatic plan generation and is
never called by `ProductionDailyRuntime`.

The operator prepares a private local JSON file outside the repository. Schema
version `1.0` requires `intent_id`, `plan_id`, inclusive dates, explicit UTC
`generated_at_utc`, version/supersession metadata, and exactly one entry for
each canonical weekday Monday through Sunday. Every entry explicitly supplies
kind, session type, duration, TSS, intensity, priority, and rationale. Existing
`TrainingIntent`, `WeeklySessionIntent`, and `TrainingPlan` validation applies;
no value is inferred.

Validate and preview without opening or creating the database:

```bash
.venv/bin/python -m scripts.bootstrap_training_plan \
  --input /absolute/private/path/to/plan.json
```

After reviewing every generated session, persist explicitly:

```bash
.venv/bin/python -m scripts.bootstrap_training_plan \
  --input /absolute/private/path/to/plan.json \
  --apply
```

Use `--training-plan-db PATH` for an explicit override. The specification's UTC
timestamp and builder-derived `{plan_id}:{date}` session IDs make retries
deterministic. Identical apply is a repository no-op; a different payload with
the same plan ID is a hard conflict. Re-run production preflight afterward.
Never commit the real specification or athlete schedule.

## BACKUP

Before the first live candidate execution:

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="data/database/backups/$STAMP"
mkdir -p "$BACKUP_DIR"
cp -p data/database/health.duckdb "$BACKUP_DIR/"
cp -p data/database/biomarkers.duckdb "$BACKUP_DIR/"
cp -p data/database/decisions.duckdb "$BACKUP_DIR/"
cp -p data/database/training_plan.duckdb "$BACKUP_DIR/"
test ! -f data/database/production_runtime.duckdb || \
  cp -p data/database/production_runtime.duckdb "$BACKUP_DIR/"
ls -l "$BACKUP_DIR"
```

The nested backup area is git-ignored. Backups are recovery insurance, not the
normal scheduler rollback.

## CUTOVER

### Preferred LaunchAgent backend

```bash
./ops/macos/install_daily_runtime_launchagent.sh --dry-run
./ops/macos/install_daily_runtime_launchagent.sh
launchctl print "gui/$(id -u)/com.athleteplatform.daily-decision-runtime"
plutil -p "$HOME/Library/LaunchAgents/com.athleteplatform.daily-decision-runtime.plist"
```

The installed arguments must contain
`scripts.run_production_daily_runtime --scheduled` and must not contain the
legacy module.

### Managed-Mac user-cron fallback

Use this only when the LaunchAgent is neither installed nor loaded. The host
timezone must remain aligned with `Europe/Warsaw`; installation fails closed
when the current abbreviation and UTC offset differ. Cron itself uses host-local
time, while the runtime continues to derive its target date with Warsaw
semantics.

```bash
./ops/macos/install_daily_runtime_cron.sh --dry-run
./ops/macos/install_daily_runtime_cron.sh
./ops/macos/status_daily_runtime_cron.sh
```

The installer owns only its clearly delimited block in the user crontab and
preserves unrelated entries. Missing, duplicated, reversed, or otherwise
malformed block markers fail closed without rewriting the crontab. A normal
macOS “no crontab” result is treated as an empty initial state; any other read
failure blocks installation and removal. Its exact cadence is `0 7-23 * * *`. Every line
uses cron's own shell to change to the repository root, set `TZ=Europe/Warsaw`,
and invoke the absolute virtualenv Python directly:

```bash
.venv/bin/python -m scripts.run_production_daily_runtime --scheduled
```

This direct topology replaces the initial repository shell-wrapper design. In
live Gate B evidence on 2026-08-12, cron fired naturally at 14:00 Warsaw time,
but macOS rejected direct execution of the wrapper from the Documents tree with
`Operation not permitted`. The runtime remained at its existing COMPLETED
revision with no new attempt or other domain mutation. The revised cron line
does not execute a repository shell file; it uses the already verified absolute
virtualenv Python path through cron's shell.

Output appends to `daily-runtime.log`; errors append to
`daily-runtime-error.log`. Independent hourly invocations are intentional:
after today's attempt is COMPLETED, scheduled policy returns an exit-0 no-op.
PARTIAL, FAILED, unsupported, unavailable, and corrupt states still fail closed;
cron does not add retries or create replacement attempts.

## VERIFY

```bash
launchctl kickstart -k gui/$(id -u)/com.athleteplatform.daily-decision-runtime
tail -n 100 "$HOME/Library/Logs/AthletePlatform/daily-runtime.log"
tail -n 100 "$HOME/Library/Logs/AthletePlatform/daily-runtime-error.log"
.venv/bin/python -m scripts.runtime_status --date "$(TZ=Europe/Warsaw date +%F)"
.venv/bin/python -m scripts.run_production_daily_runtime --scheduled
```

Record target date, runtime ID, COMPLETED revision, all eight phases,
Decision/plan/prescription IDs, briefing proof/availability, PUBLICATION,
HEALTHY, and NO_ACTION. The repeated scheduled command must be an exit-0 no-op.
Verify the loaded plist again to prove legacy is not concurrent.
For cron, use `status_daily_runtime_cron.sh` to prove the managed block is
present and no LaunchAgent or unmanaged production/legacy cron line conflicts.

## DIAGNOSTICS AND RETRY

`scripts.runtime_status` remains read-only. Scheduled policy is: no attempt →
new; resumable RUNNING → resume; COMPLETED → exit-0 no-op; terminal or corrupt
state → non-zero operator action. After correcting the cause, create an explicit
new physical attempt without changing terminal history:

```bash
.venv/bin/python -m scripts.run_production_daily_runtime \
  --new-attempt --date YYYY-MM-DD
```

## ROLLBACK

LaunchAgent rollback changes only the shared LaunchAgent configuration and
retains database history:

```bash
./ops/macos/install_daily_runtime_launchagent.sh --dry-run --legacy
./ops/macos/install_daily_runtime_launchagent.sh --legacy
launchctl print "gui/$(id -u)/com.athleteplatform.daily-decision-runtime"
plutil -p "$HOME/Library/LaunchAgents/com.athleteplatform.daily-decision-runtime.plist"
tail -n 100 "$HOME/Library/Logs/AthletePlatform/daily-runtime.log"
```

The plist must contain only `scripts.run_daily_decision_runtime`, not the new
module. Only the shared label may be loaded.

Cron rollback removes only the managed Athlete Platform block and never
schedules the legacy runtime:

```bash
./ops/macos/install_daily_runtime_cron.sh --dry-run --remove
./ops/macos/install_daily_runtime_cron.sh --remove
./ops/macos/status_daily_runtime_cron.sh
```

If legacy rollback is required, use the existing LaunchAgent rollback path
only after confirming the cron block is absent.

## COMPATIBILITY WINDOW

Keep the legacy CLI and rollback template through the first verified live run
and an agreed observation window. Removal requires separate review. Never load
legacy and production schedules concurrently.

## FINAL CLOSURE EVIDENCE

Sprint 27.7 Gate B **PASSED** on 2026-08-12. The active durable backend on this
managed Mac is user cron; LaunchAgent remains the preferred generic macOS
backend but could not be installed because `~/Library/LaunchAgents` was not
writable. Status showed an existing crontab, one present managed block, no
loaded or installed LaunchAgent, and no unmanaged runtime scheduler. Exactly
one production scheduler backend is active.

The installed schedule is:

```cron
0 7-23 * * * (cd '/Users/marsm0wa/Documents/athlete-platform' && TZ=Europe/Warsaw '/Users/marsm0wa/Documents/athlete-platform/.venv/bin/python' -m scripts.run_production_daily_runtime --scheduled) >> '/Users/marsm0wa/Library/Logs/AthletePlatform/daily-runtime.log' 2>> '/Users/marsm0wa/Library/Logs/AthletePlatform/daily-runtime-error.log'
```

Both natural scheduler observations remain part of the record. At 14:00 cron
fired, but macOS rejected direct execution of the repository wrapper with
`Operation not permitted`; this was fail-closed and produced no runtime or
domain mutation. Commit `33a25117cda3bb5e24af962e70e4ae20cb15cb08`
replaced the wrapper with direct absolute virtualenv Python execution through
cron's shell.

At 15:00:01 CEST the corrected topology fired naturally. The stdout log was
updated and reported target 2026-08-12, runtime
`runtime-6ec22727-8633-40b0-9c75-8e8b6d18db40`, COMPLETED revision 10, and
`no-op (already completed)`. The stderr log retained its 14:00 timestamp, so the
successful invocation produced no new error output. All-attempts diagnostics
still showed only the same physical runtime.

Final diagnostics were HEALTHY, NO_ACTION, not stale, and failure-free. All
eight canonical phases were represented: seven COMPLETED and RECONCILIATION
correctly SKIPPED as `reconciliation_not_applicable`. Assessment snapshot,
Decision, Training Plan, prescription, Morning Briefing, and publication all
resolved. Pre-cutover repository evidence was 27 focused cron tests, 141
ops/runtime tests, 1,682 full-suite tests, and passing `git diff --check`.

Stage 27 — Production Runtime & Reliability is **100% CLOSED**. The frozen
roadmap ends at Stage 27; further product work requires a separately approved
new roadmap / roadmap v2.
