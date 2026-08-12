#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_EXEC="$REPO_ROOT/.venv/bin/python"

cd "$REPO_ROOT"
export TZ="Europe/Warsaw"
exec "$PYTHON_EXEC" -m scripts.run_production_daily_runtime --scheduled
