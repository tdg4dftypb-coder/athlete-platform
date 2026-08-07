# Operations Manual — macOS LaunchAgent Daily Runtime

## Overview

Automated Daily Runtime for Athlete Platform is managed on macOS via `launchd` and configured through a user-level LaunchAgent.

## Architecture & Boundary

- **Scheduler Role:** External system adapter (`launchd`).
- **Domain Logic:** `DailyDecisionRuntimeCoordinator` in backend manages idempotency, CAS retry, and crash-recovery.
- **Run Date Rule:** Local day calculated using `Europe/Warsaw` timezone.
- **Idempotency Guarantee:** At-most-once per local calendar day.

## Files & Paths

- Plist Template: `ops/macos/com.athleteplatform.daily-decision-runtime.plist.template`
- Install Script: `ops/macos/install_daily_runtime_launchagent.sh`
- Uninstall Script: `ops/macos/uninstall_daily_runtime_launchagent.sh`
- Status Script: `ops/macos/status_daily_runtime_launchagent.sh`

## Standard Installation (Unmanaged macOS)

Target location:
`~/Library/LaunchAgents/com.athleteplatform.daily-decision-runtime.plist`

Log location:
`~/Library/Logs/AthletePlatform/`

```bash
# Dry run check
./ops/macos/install_daily_runtime_launchagent.sh --dry-run

# Standard Installation
./ops/macos/install_daily_runtime_launchagent.sh
```

## Managed macOS Smoke Verification

On corporate or managed Macs where `~/Library/LaunchAgents` is owned by `root`, use custom target directory overrides for testing and smoke verification:

```bash
./ops/macos/install_daily_runtime_launchagent.sh \
  --target-dir "$HOME/Library/Application Support/AthletePlatform/LaunchAgents" \
  --log-dir "$HOME/Library/Application Support/AthletePlatform/Logs"
```

This alternate-path bootstrap is intended for controlled smoke verification on managed Macs. It verifies LaunchAgent execution and daily-runtime idempotency, but it is not considered a guaranteed persistent installation after logout or reboot because the plist is outside the standard `~/Library/LaunchAgents` location.

Do not change ownership or permissions of an IT/MDM-managed `~/Library/LaunchAgents` directory manually.

## Diagnostic Commands

```bash
# Check status
./ops/macos/status_daily_runtime_launchagent.sh

# Trigger immediate execution via launchd
launchctl kickstart -k gui/$(id -u)/com.athleteplatform.daily-decision-runtime

# Test manual CLI runner directly
.venv/bin/python -m scripts.run_daily_decision_runtime
```

## Uninstallation

```bash
./ops/macos/uninstall_daily_runtime_launchagent.sh
```
