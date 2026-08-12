#!/bin/bash
set -euo pipefail

BEGIN_MARKER="# BEGIN ATHLETE PLATFORM PRODUCTION DAILY RUNTIME"
END_MARKER="# END ATHLETE PLATFORM PRODUCTION DAILY RUNTIME"
SCHEDULE="0 7-23 * * *"
LABEL="com.athleteplatform.daily-decision-runtime"
EXPECTED_TIMEZONE="Europe/Warsaw"
CRONTAB_COMMAND="${ATHLETE_PLATFORM_CRONTAB_COMMAND:-/usr/bin/crontab}"
LAUNCHCTL_COMMAND="${ATHLETE_PLATFORM_LAUNCHCTL_COMMAND:-/bin/launchctl}"
LAUNCHAGENT_DIR="${ATHLETE_PLATFORM_LAUNCHAGENT_DIR:-${HOME}/Library/LaunchAgents}"
LOG_DIR="${ATHLETE_PLATFORM_LOG_DIR:-${HOME}/Library/Logs/AthletePlatform}"
DRY_RUN=0
REMOVE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --remove) REMOVE=1; shift ;;
        *) echo "Error: unknown argument: $1" >&2; exit 2 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_EXEC="$REPO_ROOT/.venv/bin/python"
STDOUT_LOG="$LOG_DIR/daily-runtime.log"
STDERR_LOG="$LOG_DIR/daily-runtime-error.log"
PLIST="$LAUNCHAGENT_DIR/$LABEL.plist"
SERVICE="gui/$(id -u)/$LABEL"

if [[ ! -x "$PYTHON_EXEC" ]]; then
    echo "Error: Python executable is missing or not executable: $PYTHON_EXEC" >&2
    exit 1
fi
if [[ ! -x "$CRONTAB_COMMAND" ]]; then
    echo "Error: crontab command is unavailable: $CRONTAB_COMMAND" >&2
    exit 1
fi

CURRENT_FILE="$(mktemp "${TMPDIR:-/tmp}/athlete-platform-current-crontab.XXXXXX")"
ERROR_FILE="$(mktemp "${TMPDIR:-/tmp}/athlete-platform-crontab-error.XXXXXX")"
CLEAN_FILE="$(mktemp "${TMPDIR:-/tmp}/athlete-platform-clean-crontab.XXXXXX")"
NEXT_FILE="$(mktemp "${TMPDIR:-/tmp}/athlete-platform-next-crontab.XXXXXX")"
trap 'rm -f "$CURRENT_FILE" "$ERROR_FILE" "$CLEAN_FILE" "$NEXT_FILE"' EXIT

READ_STATE="existing"
if "$CRONTAB_COMMAND" -l >"$CURRENT_FILE" 2>"$ERROR_FILE"; then
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

if [[ "$MANAGED_STATE" == "present" ]]; then
    awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
        $0 == begin { managed=1; next }
        $0 == end { managed=0; next }
        !managed { print }
    ' "$CURRENT_FILE" >"$CLEAN_FILE"
else
    cp "$CURRENT_FILE" "$CLEAN_FILE"
fi

UNMANAGED_CONFLICTS="$(grep -E '^[[:space:]]*[^#].*(scripts\.run_production_daily_runtime|scripts\.run_daily_decision_runtime|run_production_daily_runtime_cron\.sh)' "$CLEAN_FILE" || true)"
LOADED_CONFLICT=0
if [[ -x "$LAUNCHCTL_COMMAND" ]] && "$LAUNCHCTL_COMMAND" print "$SERVICE" >/dev/null 2>&1; then
    LOADED_CONFLICT=1
fi
INSTALLED_CONFLICT=0
[[ -f "$PLIST" ]] && INSTALLED_CONFLICT=1

EXPECTED_TZ="$(TZ="$EXPECTED_TIMEZONE" date '+%Z %z')"
HOST_TZ="$(date '+%Z %z')"
if [[ -n "${ATHLETE_PLATFORM_EXPECTED_TIMEZONE_SIGNATURE:-}" ]]; then
    EXPECTED_TZ="$ATHLETE_PLATFORM_EXPECTED_TIMEZONE_SIGNATURE"
fi
if [[ -n "${ATHLETE_PLATFORM_HOST_TIMEZONE_SIGNATURE:-}" ]]; then
    HOST_TZ="$ATHLETE_PLATFORM_HOST_TIMEZONE_SIGNATURE"
fi
TIMEZONE_ALIGNED=0
[[ "$HOST_TZ" == "$EXPECTED_TZ" ]] && TIMEZONE_ALIGNED=1

BLOCK="$BEGIN_MARKER
$SCHEDULE (cd '$REPO_ROOT' && TZ=$EXPECTED_TIMEZONE '$PYTHON_EXEC' -m scripts.run_production_daily_runtime --scheduled) >> '$STDOUT_LOG' 2>> '$STDERR_LOG'
$END_MARKER"

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "=== DRY RUN: Athlete Platform user cron ==="
    echo "Operation          : $([[ "$REMOVE" -eq 1 ]] && echo remove || echo install)"
    echo "Crontab read       : $READ_STATE"
    echo "Managed cron block : $MANAGED_STATE"
    echo "Schedule           : $SCHEDULE"
    echo "Repository         : $REPO_ROOT"
    echo "Python             : $PYTHON_EXEC"
    echo "Canonical command  : cd '$REPO_ROOT' && TZ=$EXPECTED_TIMEZONE '$PYTHON_EXEC' -m scripts.run_production_daily_runtime --scheduled"
    echo "Log stdout         : $STDOUT_LOG"
    echo "Log stderr         : $STDERR_LOG"
    echo "Timezone expected  : $EXPECTED_TZ ($EXPECTED_TIMEZONE)"
    echo "Timezone host      : $HOST_TZ"
    echo "Timezone aligned   : $([[ "$TIMEZONE_ALIGNED" -eq 1 ]] && echo yes || echo no)"
    echo "LaunchAgent loaded : $([[ "$LOADED_CONFLICT" -eq 1 ]] && echo conflict || echo no)"
    echo "LaunchAgent plist  : $([[ "$INSTALLED_CONFLICT" -eq 1 ]] && echo conflict || echo no)"
    echo "Unmanaged runtime  : $([[ -n "$UNMANAGED_CONFLICTS" ]] && echo conflict || echo no)"
    if [[ "$READ_STATE" == "error" ]]; then
        echo "Crontab read error : $(tr '\n' ' ' <"$ERROR_FILE")"
    fi
    if [[ "$REMOVE" -eq 1 ]]; then
        echo "Resulting intent   : managed block absent; unrelated entries preserved"
    else
        echo "--- Proposed managed block ---"
        printf '%s\n' "$BLOCK"
    fi
    exit 0
fi

if [[ "$READ_STATE" == "error" ]]; then
    echo "Error: unable to read user crontab: $(tr '\n' ' ' <"$ERROR_FILE")" >&2
    exit 1
fi
if [[ "$MANAGED_STATE" == "malformed" ]]; then
    echo "Error: managed Athlete Platform cron markers are malformed" >&2
    exit 1
fi
if [[ "$REMOVE" -eq 1 && "$MANAGED_STATE" == "absent" ]]; then
    echo "No Athlete Platform managed cron block is installed; nothing to remove."
    exit 0
fi

if [[ "$REMOVE" -eq 0 ]]; then
    if [[ "$TIMEZONE_ALIGNED" -ne 1 ]]; then
        echo "Error: host timezone '$HOST_TZ' is not aligned with $EXPECTED_TIMEZONE ('$EXPECTED_TZ')" >&2
        exit 1
    fi
    if [[ "$LOADED_CONFLICT" -eq 1 || "$INSTALLED_CONFLICT" -eq 1 ]]; then
        echo "Error: Athlete Platform LaunchAgent is installed or loaded; remove it explicitly before cron installation" >&2
        exit 1
    fi
    if [[ -n "$UNMANAGED_CONFLICTS" ]]; then
        echo "Error: unmanaged Athlete Platform runtime cron entry exists" >&2
        exit 1
    fi
    mkdir -p "$LOG_DIR"
fi

cp "$CLEAN_FILE" "$NEXT_FILE"
if [[ "$REMOVE" -eq 0 ]]; then
    if [[ -s "$NEXT_FILE" ]]; then
        printf '%s\n' "$BLOCK" >>"$NEXT_FILE"
    else
        printf '%s\n' "$BLOCK" >"$NEXT_FILE"
    fi
fi
if ! "$CRONTAB_COMMAND" "$NEXT_FILE"; then
    echo "Error: failed to update user crontab" >&2
    exit 1
fi
echo "$([[ "$REMOVE" -eq 1 ]] && echo Removed || echo Installed) Athlete Platform managed cron block."
