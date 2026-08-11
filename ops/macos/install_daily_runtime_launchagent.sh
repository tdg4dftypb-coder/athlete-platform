#!/bin/bash
set -euo pipefail

# Installer script for Athlete Platform Automated Daily Decision Runtime LaunchAgent

LABEL="com.athleteplatform.daily-decision-runtime"
DEFAULT_HOUR=7
DEFAULT_MINUTE=0
DEFAULT_TIMEZONE="Europe/Warsaw"
DEFAULT_TARGET_DIR="${HOME}/Library/LaunchAgents"
DEFAULT_LOG_DIR="${HOME}/Library/Logs/AthletePlatform"
DRY_RUN=0
LEGACY=0

HOUR="$DEFAULT_HOUR"
MINUTE="$DEFAULT_MINUTE"
TIMEZONE="$DEFAULT_TIMEZONE"
TARGET_DIR="$DEFAULT_TARGET_DIR"
LOG_DIR="$DEFAULT_LOG_DIR"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --hour)
            HOUR="$2"
            shift 2
            ;;
        --minute)
            MINUTE="$2"
            shift 2
            ;;
        --timezone)
            TIMEZONE="$2"
            shift 2
            ;;
        --target-dir)
            TARGET_DIR="$2"
            shift 2
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --legacy)
            LEGACY=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

# Validate Hour & Minute
if ! [[ "$HOUR" =~ ^[0-9]+$ ]] || [ "$HOUR" -lt 0 ] || [ "$HOUR" -gt 23 ]; then
    echo "Error: Hour must be between 0 and 23" >&2
    exit 2
fi

if ! [[ "$MINUTE" =~ ^[0-9]+$ ]] || [ "$MINUTE" -lt 0 ] || [ "$MINUTE" -gt 59 ]; then
    echo "Error: Minute must be between 0 and 59" >&2
    exit 2
fi

# Resolve Repo Root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PYTHON_EXEC="$REPO_ROOT/.venv/bin/python"
if [ "$LEGACY" -eq 1 ]; then
    SCRIPT_TARGET="$REPO_ROOT/scripts/run_daily_decision_runtime.py"
    TEMPLATE_FILE="$REPO_ROOT/ops/macos/$LABEL.legacy.plist.template"
    RUNTIME_MODE="legacy rollback"
else
    SCRIPT_TARGET="$REPO_ROOT/scripts/run_production_daily_runtime.py"
    TEMPLATE_FILE="$REPO_ROOT/ops/macos/$LABEL.plist.template"
    RUNTIME_MODE="production scheduled"
fi

# Validate Python environment & target script
if [ ! -x "$PYTHON_EXEC" ]; then
    echo "Error: Python executable not found or not executable at $PYTHON_EXEC" >&2
    exit 1
fi

if [ ! -f "$SCRIPT_TARGET" ]; then
    echo "Error: Target daily script not found at $SCRIPT_TARGET" >&2
    exit 1
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Plist template not found at $TEMPLATE_FILE" >&2
    exit 1
fi

PLIST_TARGET="$TARGET_DIR/$LABEL.plist"
LOG_STDOUT="$LOG_DIR/daily-runtime.log"
LOG_STDERR="$LOG_DIR/daily-runtime-error.log"

# Render Plist
RENDERED_PLIST=$(cat "$TEMPLATE_FILE" \
    | sed "s|__PYTHON_PATH__|$PYTHON_EXEC|g" \
    | sed "s|__WORKING_DIR__|$REPO_ROOT|g" \
    | sed "s|__START_HOUR__|$HOUR|g" \
    | sed "s|__START_MINUTE__|$MINUTE|g" \
    | sed "s|__TIMEZONE__|$TIMEZONE|g" \
    | sed "s|__LOG_STDOUT__|$LOG_STDOUT|g" \
    | sed "s|__LOG_STDERR__|$LOG_STDERR|g")

# Dry Run Output
if [ "$DRY_RUN" -eq 1 ]; then
    echo "=== DRY RUN: LaunchAgent Configuration ==="
    echo "Target Plist Path : $PLIST_TARGET"
    echo "Python Executable : $PYTHON_EXEC"
    echo "Working Directory : $REPO_ROOT"
    echo "Schedule          : $HOUR:$MINUTE ($TIMEZONE)"
    echo "Runtime Mode      : $RUNTIME_MODE"
    echo "Log Stdout        : $LOG_STDOUT"
    echo "Log Stderr        : $LOG_STDERR"
    echo ""
    echo "--- Rendered Content ---"
    echo "$RENDERED_PLIST"
    echo "------------------------"

    # Lint validation via plutil
    echo "$RENDERED_PLIST" | plutil -lint - > /dev/null
    echo "plutil lint check : OK"
    exit 0
fi

# Real Installation Directory & Writable Validations
if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR" 2>/dev/null || {
        echo "Error: Cannot create target directory '$TARGET_DIR'. Permission denied." >&2
        exit 1
    }
fi

if [ ! -w "$TARGET_DIR" ]; then
    echo "Error: Target directory '$TARGET_DIR' is not writable. Permission denied." >&2
    exit 1
fi

if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR" 2>/dev/null || {
        echo "Error: Cannot create log directory '$LOG_DIR'. Permission denied." >&2
        exit 1
    }
fi

if [ ! -w "$LOG_DIR" ]; then
    echo "Error: Log directory '$LOG_DIR' is not writable. Permission denied." >&2
    exit 1
fi

# Write & Lint Plist
echo "$RENDERED_PLIST" > "$PLIST_TARGET"
plutil -lint "$PLIST_TARGET" > /dev/null

USER_ID=$(id -u)
DOMAIN_TARGET="gui/$USER_ID"
SERVICE_TARGET="$DOMAIN_TARGET/$LABEL"

# Bootout previous agent if running/loaded
if launchctl print "$SERVICE_TARGET" > /dev/null 2>&1; then
    launchctl bootout "$SERVICE_TARGET" 2>/dev/null || true
fi

# Bootstrap new agent
launchctl bootstrap "$DOMAIN_TARGET" "$PLIST_TARGET"

echo "LaunchAgent installed and bootstrapped successfully."
echo "Label    : $LABEL"
echo "Plist    : $PLIST_TARGET"
echo "Schedule : $HOUR:$MINUTE ($TIMEZONE)"
