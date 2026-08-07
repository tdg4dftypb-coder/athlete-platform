#!/bin/bash
set -euo pipefail

# Uninstaller script for Athlete Platform Automated Daily Decision Runtime LaunchAgent

LABEL="com.athleteplatform.daily-decision-runtime"
DEFAULT_TARGET_DIR="${HOME}/Library/LaunchAgents"
TARGET_DIR="$DEFAULT_TARGET_DIR"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-dir)
            TARGET_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

PLIST_TARGET="$TARGET_DIR/$LABEL.plist"
USER_ID=$(id -u)
DOMAIN_TARGET="gui/$USER_ID"
SERVICE_TARGET="$DOMAIN_TARGET/$LABEL"

if launchctl print "$SERVICE_TARGET" > /dev/null 2>&1; then
    launchctl bootout "$SERVICE_TARGET" || true
    echo "Booted out launchd agent $LABEL"
else
    echo "LaunchAgent $LABEL was not loaded in launchd"
fi

if [ -f "$PLIST_TARGET" ]; then
    rm -f "$PLIST_TARGET"
    echo "Removed plist at $PLIST_TARGET"
else
    echo "Plist $PLIST_TARGET does not exist"
fi

echo "Uninstallation complete."
