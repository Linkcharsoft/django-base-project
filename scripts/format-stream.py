#!/usr/bin/env python3
"""Pretty-print a stream-json log from `claude -p --output-format stream-json`.

Reads one JSON event per line from stdin and writes a human-readable line
to stdout. Used by both `scripts/run-tasks.sh` (live pipe) and
`scripts/pretty-log.sh` (replay a saved log).
"""

from __future__ import annotations

import json
import sys

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DARK = "\033[90m"
RESET = "\033[0m"

INPUT_FIELDS = (
    "file_path",
    "path",
    "command",
    "pattern",
    "description",
    "subagent_type",
    "prompt",
)


def truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def format_event(line: str) -> None:
    line = line.rstrip("\r\n")
    if not line.strip():
        return
    try:
        evt = json.loads(line)
    except json.JSONDecodeError:
        print(line)
        return

    t = evt.get("type")

    if t == "system" and evt.get("subtype") == "init":
        print(f"{DARK}[init] session {evt.get('session_id', '')}{RESET}")
        return

    if t == "assistant":
        for block in evt.get("message", {}).get("content", []) or []:
            bt = block.get("type")
            if bt == "text":
                text = block.get("text")
                if text:
                    print(text)
            elif bt == "tool_use":
                name = block.get("name", "")
                brief = ""
                inp = block.get("input") or {}
                for f in INPUT_FIELDS:
                    val = inp.get(f)
                    if val:
                        brief = f"{f}={truncate(str(val), 140)}"
                        break
                print(f"{CYAN}  -> {name} {brief}{RESET}")
        return

    if t == "user":
        for block in evt.get("message", {}).get("content", []) or []:
            if block.get("type") == "tool_result":
                content = truncate(str(block.get("content", "")), 200)
                color = RED if block.get("is_error") else DARK
                print(f"{color}  <- {content}{RESET}")
        return

    if t == "result":
        print()
        print(f"{GREEN}=== RESULT ({evt.get('subtype', '')}) ==={RESET}")
        result = evt.get("result")
        if result:
            print(result)
        cost = evt.get("total_cost_usd")
        if cost is not None:
            dur = round((evt.get("duration_ms", 0) or 0) / 1000, 1)
            print(f"{DARK}cost: ${round(cost, 4)}  duration: {dur}s{RESET}")
        print()


def main() -> int:
    for line in sys.stdin:
        format_event(line)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
