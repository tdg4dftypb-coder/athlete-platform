# Operations Manual — macOS Production Daily Runtime Cutover

Gate A prepares this procedure but does not execute it. Gate B is manual.
The single user LaunchAgent label is
`com.athleteplatform.daily-decision-runtime`; cadence remains 07:00 local time
with `RunAtLoad=true`, repository-root `WorkingDirectory`, `.venv/bin/python`,
and logs under `~/Library/Logs/AthletePlatform`.

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

```bash
./ops/macos/install_daily_runtime_launchagent.sh --dry-run
./ops/macos/install_daily_runtime_launchagent.sh
launchctl print "gui/$(id -u)/com.athleteplatform.daily-decision-runtime"
plutil -p "$HOME/Library/LaunchAgents/com.athleteplatform.daily-decision-runtime.plist"
```

The installed arguments must contain
`scripts.run_production_daily_runtime --scheduled` and must not contain the
legacy module.

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

Rollback changes only the one LaunchAgent configuration and retains database
history:

```bash
./ops/macos/install_daily_runtime_launchagent.sh --dry-run --legacy
./ops/macos/install_daily_runtime_launchagent.sh --legacy
launchctl print "gui/$(id -u)/com.athleteplatform.daily-decision-runtime"
plutil -p "$HOME/Library/LaunchAgents/com.athleteplatform.daily-decision-runtime.plist"
tail -n 100 "$HOME/Library/Logs/AthletePlatform/daily-runtime.log"
```

The plist must contain only `scripts.run_daily_decision_runtime`, not the new
module. Only the shared label may be loaded.

## COMPATIBILITY WINDOW

Keep the legacy CLI and rollback template through the first verified live run
and an agreed observation window. Removal requires separate review. Never load
legacy and production schedules concurrently.

## FINAL CLOSURE EVIDENCE

Gate A leaves Stage 27 at 90%. Gate B must record the first live runtime ID,
Warsaw date, COMPLETED revision, eight phases, HEALTHY/NO_ACTION diagnostics,
new loaded command, no concurrent legacy schedule, rollback availability, and
the green suite. Only then may the roadmap state 100% CLOSED.
