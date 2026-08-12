#!/bin/bash
set -euo pipefail

BEGIN_MARKER="# BEGIN ATHLETE PLATFORM PRODUCTION DAILY RUNTIME"
END_MARKER="# END ATHLETE PLATFORM PRODUCTION DAILY RUNTIME"
LABEL="com.athleteplatform.daily-decision-runtime"
CRONTAB_COMMAND="${ATHLETE_PLATFORM_CRONTAB_COMMAND:-/usr/bin/crontab}"
LAUNCHCTL_COMMAND="${ATHLETE_PLATFORM_LAUNCHCTL_COMMAND:-/bin/launchctl}"
LAUNCHAGENT_DIR="${ATHLETE_PLATFORM_LAUNCHAGENT_DIR:-${HOME}/Library/LaunchAgents}"
LOG_DIR="${ATHLETE_PLATFORM_LOG_DIR:-${HOME}/Library/Logs/AthletePlatform}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$REPO_ROOT/ops/macos/run_production_daily_runtime_cron.sh"
SERVICE="gui/$(id -u)/$LABEL"

CURRENT_FILE="$(mktemp "${TMPDIR:-/tmp}/athlete-platform-status-crontab.XXXXXX")"
ERROR_FILE="$(mktemp "${TMPDIR:-/tmp}/athlete-platform-status-error.XXXXXX")"
CLEAN_FILE="$(mktemp "${TMPDIR:-/tmp}/athlete-platform-status-clean.XXXXXX")"
trap 'rm -f "$CURRENT_FILE" "$ERROR_FILE" "$CLEAN_FILE"' EXIT

READ_STATE="existing"
if [[ ! -x "$CRONTAB_COMMAND" ]]; then
    READ_STATE="error"
    echo "crontab command unavailable: $CRONTAB_COMMAND" >"$ERROR_FILE"
elif "$CRONTAB_COMMAND" -l >"$CURRENT_FILE" 2>"$ERROR_FILE"; then
    :
elif grep -Eiq '(^|: )[Nn]o crontab for [^[:space:]]+' "$ERROR_FILE"; then
    READ_STATE="absent"
    : >"$CURRENT_FILE"
else
    READ_STATE="error"
fi

BEGIN_COUNT="$(grep -Fxc "$BEGIN_MARKER" "$CURRENT_FILE" || true)"
END_COUNT="$(grep -Fxc "$END_MARKER" "$CURRENT_FILE" || true)"
MANAGED_STATE="absent"
if [[ "$READ_STATE" == "error" ]]; then
    MANAGED_STATE="unknown"
elif [[ "$BEGIN_COUNT" -eq 1 && "$END_COUNT" -eq 1 ]]; then
    BEGIN_LINE="$(grep -Fn "$BEGIN_MARKER" "$CURRENT_FILE" | cut -d: -f1)"
    END_LINE="$(grep -Fn "$END_MARKER" "$CURRENT_FILE" | cut -d: -f1)"
    if [[ "$BEGIN_LINE" -lt "$END_LINE" ]]; then
        MANAGED_STATE="present"
    else
        MANAGED_STATE="malformed"
    fi
elif [[ "$BEGIN_COUNT" -ne 0 || "$END_COUNT" -ne 0 ]]; then
    MANAGED_STATE="malformed"
fi

MANAGED_LINE="none"
if [[ "$MANAGED_STATE" == "present" ]]; then
    MANAGED_LINE="$(awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
        $0 == begin { managed=1; next }
        $0 == end { managed=0; next }
        managed { print }
    ' "$CURRENT_FILE")"
    awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
        $0 == begin { managed=1; next }
        $0 == end { managed=0; next }
        !managed { print }
    ' "$CURRENT_FILE" >"$CLEAN_FILE"
else
    cp "$CURRENT_FILE" "$CLEAN_FILE"
fi
UNMANAGED_CONFLICTS="$(grep -E "^[[:space:]]*[^#].*(scripts\\.run_production_daily_runtime|scripts\\.run_daily_decision_runtime|run_production_daily_runtime_cron\\.sh|${WRAPPER//\//\\/})" "$CLEAN_FILE" || true)"
LOADED=0
if [[ -x "$LAUNCHCTL_COMMAND" ]] && "$LAUNCHCTL_COMMAND" print "$SERVICE" >/dev/null 2>&1; then
    LOADED=1
fi

echo "Crontab read       : $READ_STATE"
echo "Managed cron block : $MANAGED_STATE"
echo "Managed schedule   : $([[ "$MANAGED_STATE" == present ]] && echo "$MANAGED_LINE" || echo none)"
echo "Wrapper            : $WRAPPER"
echo "Log stdout         : $LOG_DIR/daily-runtime.log"
echo "Log stderr         : $LOG_DIR/daily-runtime-error.log"
echo "LaunchAgent loaded : $([[ "$LOADED" -eq 1 ]] && echo conflict || echo no)"
echo "LaunchAgent plist  : $([[ -f "$LAUNCHAGENT_DIR/$LABEL.plist" ]] && echo conflict || echo no)"
echo "Unmanaged runtime  : $([[ -n "$UNMANAGED_CONFLICTS" ]] && echo conflict || echo no)"
if [[ "$READ_STATE" == "error" ]]; then
    echo "Crontab read error : $(tr '\n' ' ' <"$ERROR_FILE")"
fi
