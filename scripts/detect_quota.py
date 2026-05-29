#!/usr/bin/env python3
"""Detect Claude Code quota exhaustion in a stream-json iteration log.

Only Pro / Max plans are in scope (the loop is never run against the raw
API), so the two failure modes we care about are:

1. **5-hour session window exhausted** — recoverable: sleep until the
   window resets and continue the loop.
2. **Weekly cap exhausted** — not recoverable inside one run: signal the
   bash caller to stop the loop.

Reads the log file given as ``argv[1]`` and prints exactly one line:

    SESSION <epoch>   — session window exhausted, reset epoch parsed
    SESSION           — session window exhausted, no reset time parsed
    WEEKLY            — weekly cap hit, give up
    (nothing)         — no quota issue

Always exits 0 so the bash caller can use captured stdout cleanly.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

WEEKLY_PATTERNS = [
    re.compile(r"weekly\s+(?:limit|usage|cap)", re.IGNORECASE),
    re.compile(r"weekly_limit", re.IGNORECASE),
]

SESSION_PATTERNS = [
    re.compile(r"\busage limit reached\b", re.IGNORECASE),
    re.compile(r"\b5-?hour limit\b", re.IGNORECASE),
    re.compile(r"\bsession limit\b", re.IGNORECASE),
    re.compile(r"claude_ai_usage_limit_reached", re.IGNORECASE),
    re.compile(r"usage_limit_exceeded", re.IGNORECASE),
]

RESET_PATTERNS = [
    re.compile(r'"reset[_a-z]*"\s*:\s*(\d{10})'),
    re.compile(r"resets?\s+at\s+(\d{10})\b", re.IGNORECASE),
    re.compile(
        r"resets?\s+at\s+" r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)",
        re.IGNORECASE,
    ),
]


def parse_iso(s: str) -> int | None:
    try:
        s = s.replace("Z", "+00:00").replace(" ", "T")
        return int(datetime.fromisoformat(s).timestamp())
    except ValueError:
        return None


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    path = Path(sys.argv[1])
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")

    if any(p.search(text) for p in WEEKLY_PATTERNS):
        print("WEEKLY")
        return 0

    if not any(p.search(text) for p in SESSION_PATTERNS):
        return 0

    for rx in RESET_PATTERNS:
        m = rx.search(text)
        if not m:
            continue
        raw = m.group(1)
        epoch = int(raw) if raw.isdigit() else parse_iso(raw)
        if epoch:
            print(f"SESSION {epoch}")
            return 0

    print("SESSION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
