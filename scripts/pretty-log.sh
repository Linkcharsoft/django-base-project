#!/usr/bin/env bash
# Pretty-print a stream-json log produced by run-tasks.sh (or any
# `claude -p --output-format stream-json` invocation).
#
# Usage:
#   bash scripts/pretty-log.sh logs/run-tasks-20260521-144237.log
#   bash scripts/pretty-log.sh --follow logs/run-tasks-20260521-144237.log
#   just task-log logs/run-tasks-20260521-144237.log

set -euo pipefail

FOLLOW=0
LOG_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--follow) FOLLOW=1; shift ;;
        -h|--help)
            sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) LOG_PATH="$1"; shift ;;
    esac
done

if [[ -z "$LOG_PATH" ]]; then
    echo "ERROR: missing log path. Usage: bash scripts/pretty-log.sh <path>" >&2
    exit 2
fi
if [[ ! -f "$LOG_PATH" ]]; then
    echo "ERROR: log not found: $LOG_PATH" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$FOLLOW" -eq 1 ]]; then
    tail -n +1 -f "$LOG_PATH" | python3 "$SCRIPT_DIR/format-stream.py"
else
    python3 "$SCRIPT_DIR/format-stream.py" < "$LOG_PATH"
fi
