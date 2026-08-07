#!/bin/bash
set -euo pipefail

# Status checker script for Athlete Platform Automated Daily Decision Runtime LaunchAgent

LABEL="com.athleteplatform.daily-decision-runtime"
DEFAULT_TARGET_DIR="${HOME}/Library/LaunchAgents"
DEFAULT_LOG_DIR="${HOME}/Library/Logs/AthletePlatform"
TARGET_DIR="$DEFAULT_TARGET_DIR"
LOG_DIR="$DEFAULT_LOG_DIR"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-dir)
            TARGET_DIR="$2"
            shift 2
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

PLIST_TARGET="$TARGET_DIR/$LABEL.plist"
LOG_STDOUT="$LOG_DIR/daily-runtime.log"
LOG_STDERR="$LOG_DIR/daily-runtime-error.log"

USER_ID=$(id -u)
SERVICE_TARGET="gui/$USER_ID/$LABEL"

echo "=== Automated Daily Runtime LaunchAgent Status ==="
echo "Label         : $LABEL"

if [ -f "$PLIST_TARGET" ]; then
    echo "Plist File    : INSTALLED ($PLIST_TARGET)"
else
    echo "Plist File    : NOT INSTALLED ($PLIST_TARGET)"
fi

if launchctl print "$SERVICE_TARGET" > /dev/null 2>&1; then
    echo "Launchd State : LOADED"
else
    echo "Launchd State : NOT LOADED"
fi

echo "Log Stdout    : $LOG_STDOUT"
echo "Log Stderr    : $LOG_STDERR"

if [ -f "$LOG_STDOUT" ]; then
    echo "--- Latest Stdout Log (Last 5 lines) ---"
    tail -n 5 "$LOG_STDOUT" || true
    echo "----------------------------------------"
fi

if [ -f "$LOG_STDERR" ] && [ -s "$LOG_STDERR" ]; then
    echo "--- Latest Stderr Log (Last 5 lines) ---"
    tail -n 5 "$LOG_STDERR" || true
    echo "----------------------------------------"
fi
