#!/usr/bin/env bash
# Task loop runner. Picks pending tasks from tasks.md, invokes the
# django-task-runner subagent on each, stops when no pending remain or
# when the agent makes no progress N times in a row.
#
# Usage:
#   bash scripts/run-tasks.sh
#   bash scripts/run-tasks.sh --max-stalled 5
#   bash scripts/run-tasks.sh --tasks-file other.md --max-turns 120
#   bash scripts/run-tasks.sh --max-quota-wait 28800   # cap quota sleeps at 8h
#
# Wired through justfile as `just task-run`. Cross-platform (Linux, macOS,
# Windows via git-bash). Requires: bash, git, python3, claude CLI.
#
# Quota handling: when the Claude 5-hour session window is exhausted mid-loop
# (Pro/Max plans), the script sleeps until reset and continues — designed
# for overnight runs that pick up across multiple sessions. A weekly cap hit
# aborts the loop since there is nothing to wait for.

set -euo pipefail

TASKS_FILE="tasks.md"
MAX_STALLED=3
MAX_TURNS=80
# Hard ceiling on a single quota-wait. If Claude says reset is further than
# this, abort instead of sleeping. 12h covers an overnight run that lands on
# two consecutive 5-hour windows with a long gap.
MAX_QUOTA_WAIT=43200

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tasks-file) TASKS_FILE="$2"; shift 2 ;;
        --max-stalled) MAX_STALLED="$2"; shift 2 ;;
        --max-turns) MAX_TURNS="$2"; shift 2 ;;
        --max-quota-wait) MAX_QUOTA_WAIT="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

YELLOW=$'\033[33m'
RED=$'\033[31m'
CYAN=$'\033[36m'
GREEN=$'\033[32m'
RESET=$'\033[0m'

count_pending() {
    [[ -f "$TASKS_FILE" ]] || { echo 0; return; }
    # grep -c prints "0" AND exits 1 when there are no matches; swallow the
    # exit so we keep the count without doubling it via `|| echo 0`.
    grep -c '^\*\*Status\*\*: pending' "$TASKS_FILE" || true
}

format_epoch() {
    # Print an epoch as "YYYY-MM-DD HH:MM" in local time, cross-platform.
    python3 -c "import datetime, sys; print(datetime.datetime.fromtimestamp(int(sys.argv[1])).strftime('%Y-%m-%d %H:%M'))" "$1"
}

# Handle a quota event detected on the just-finished iteration. Reads stdin:
# either "SESSION <epoch>", "SESSION", or "WEEKLY".
# Returns:
#   0  — handled; caller should `continue` the loop without counting a stall.
#   1  — weekly cap; caller should exit the loop.
#   2  — reset is further than --max-quota-wait; caller should exit.
handle_quota() {
    local verdict="$1"
    if [[ "$verdict" == WEEKLY ]]; then
        echo "${RED}[x] Weekly usage cap reached. Nothing to wait for — aborting the loop.${RESET}" >&2
        return 1
    fi

    local reset_epoch=""
    if [[ "$verdict" == "SESSION "* ]]; then
        reset_epoch="${verdict#SESSION }"
    fi

    local wait_seconds
    if [[ -n "$reset_epoch" ]]; then
        local now
        now=$(date +%s)
        wait_seconds=$((reset_epoch - now + 60))  # +60s buffer for clock skew
        if (( wait_seconds < 60 )); then
            wait_seconds=60
        fi
        if (( wait_seconds > MAX_QUOTA_WAIT )); then
            echo "${RED}[x] Session resets in ${wait_seconds}s, exceeds --max-quota-wait (${MAX_QUOTA_WAIT}). Aborting.${RESET}" >&2
            return 2
        fi
        local human
        human=$(format_epoch "$reset_epoch")
        echo "${YELLOW}[~] Session window exhausted. Waiting until $human (${wait_seconds}s) for the next session. Ctrl-C to abort.${RESET}"
    else
        # No reset time parseable — fall back to a conservative 15-minute poll.
        wait_seconds=900
        echo "${YELLOW}[~] Session window exhausted (reset time not parseable from log). Sleeping ${wait_seconds}s before retry. Ctrl-C to abort.${RESET}"
    fi

    sleep "$wait_seconds"
    return 0
}

report_setup() {
    [[ -f SETUP_REQUIRED.md ]] || return 0
    local count
    count=$(grep -c '^- \[ \]' SETUP_REQUIRED.md || true)
    count=${count:-0}
    if [[ "$count" -gt 0 ]]; then
        echo ""
        echo "${YELLOW}[!] ${count} item(s) in SETUP_REQUIRED.md still need manual configuration.${RESET}"
    fi
}

if [[ ! -f "$TASKS_FILE" ]]; then
    echo "${RED}ERROR: $TASKS_FILE not found. Copy tasks.md.example to tasks.md and fill it in.${RESET}" >&2
    exit 1
fi

# Refuse to run on the protected branches. The builder commits after every task,
# so we don't want it polluting main/master. Check out a dedicated branch first
# (convention in this repo: `claude-tasks`).
if ! current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null); then
    echo "${RED}ERROR: could not detect current git branch (not a git repo, or detached HEAD).${RESET}" >&2
    exit 1
fi
if [[ "$current_branch" == "main" || "$current_branch" == "master" ]]; then
    echo "${RED}ERROR: refusing to run on '$current_branch'. The builder will commit after every task. Run 'git checkout -b claude-tasks' (or pick another branch) and retry.${RESET}" >&2
    exit 1
fi

# Locate claude CLI: PATH first, then ~/.local/bin (claude or claude.exe under git-bash on Windows).
if ! command -v claude >/dev/null 2>&1; then
    for cand in "$HOME/.local/bin/claude" "$HOME/.local/bin/claude.exe"; do
        if [[ -x "$cand" ]]; then
            export PATH="$HOME/.local/bin:$PATH"
            break
        fi
    done
    if ! command -v claude >/dev/null 2>&1; then
        echo "${RED}ERROR: claude CLI not found on PATH nor in ~/.local/bin.${RESET}" >&2
        exit 1
    fi
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "${RED}ERROR: python3 is required for stream-json formatting.${RESET}" >&2
    exit 1
fi

# Docker must be reachable: every task verifies via `just lint`/`just test`/
# `just schema-validate`, which all run inside the web container. Failing here
# is cheaper than letting the first task burn turns on a broken environment.
if ! command -v docker >/dev/null 2>&1; then
    echo "${RED}ERROR: docker CLI not found on PATH. Install Docker Desktop and retry.${RESET}" >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "${RED}ERROR: Docker daemon is not reachable. Start Docker Desktop (or the docker service) and retry.${RESET}" >&2
    exit 1
fi

mkdir -p logs
run_log="logs/run-tasks-$(date +%Y%m%d-%H%M%S).log"

echo "${CYAN}=== Task Runner ===${RESET}"
echo "tasks file:  $TASKS_FILE"
echo "log:         $run_log"
echo "pending:     $(count_pending)"
echo ""

stalled=0
iteration=0

prompt="Use the Task tool with subagent_type=django-task-runner. Read tasks.md, pick the first task whose status is 'pending', implement it end-to-end per the agent's instructions, mark it done, write the progress note, and stop. Do not pick a second task."

while [[ "$(count_pending)" -gt 0 ]]; do
    iteration=$((iteration + 1))
    pending_before=$(count_pending)

    echo ""
    echo "${CYAN}>> Iteration $iteration ($pending_before pending)${RESET}"

    {
        echo ""
        echo "=== Iteration $iteration @ $(date -Iseconds) ($pending_before pending) ==="
    } >> "$run_log"

    # Stream raw JSONL to the log (audit trail) AND pretty-print live to the host.
    # The per-iteration copy under iter_log is what the quota detector reads.
    iter_log="logs/iter-$$-$iteration.log"
    set +e
    claude -p --output-format stream-json --verbose --include-partial-messages \
        --max-turns "$MAX_TURNS" "$prompt" 2>&1 \
        | tee -a "$run_log" \
        | tee "$iter_log" \
        | python3 "$SCRIPT_DIR/format-stream.py"
    set -e

    # Check for a Claude quota event before evaluating progress. A session
    # window exhaustion looks like "no progress" but shouldn't count as a
    # stall — we just wait and retry the same task.
    quota_verdict=$(python3 "$SCRIPT_DIR/detect_quota.py" "$iter_log")
    rm -f "$iter_log"
    if [[ -n "$quota_verdict" ]]; then
        if handle_quota "$quota_verdict"; then
            continue
        else
            report_setup
            exit 1
        fi
    fi

    pending_after=$(count_pending)

    if [[ "$pending_after" -ge "$pending_before" ]]; then
        stalled=$((stalled + 1))
        echo "${YELLOW}[!] No progress ($pending_after still pending). Stall $stalled/$MAX_STALLED${RESET}"
        if [[ "$stalled" -ge "$MAX_STALLED" ]]; then
            echo "${RED}[x] Agent is not advancing tasks. Inspect $TASKS_FILE and $run_log.${RESET}"
            report_setup
            exit 1
        fi
    else
        stalled=0
        echo "${GREEN}[ok] Task completed ($pending_before -> $pending_after pending)${RESET}"
    fi
done

echo ""
echo "${GREEN}=== All tasks completed ===${RESET}"
report_setup
