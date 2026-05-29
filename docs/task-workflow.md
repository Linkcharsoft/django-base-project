# Task workflow (autonomous subagents)

**Scope.** The planner → runner → reviewer loop driven by `tasks.md`, the `claude` CLI, and `just task-run` / `just review`. Not covered: the agent definitions themselves (see [`.claude/agents/`](../.claude/agents/)) and the repo-local skills they invoke (see [`.claude/skills/`](../.claude/skills/)).

## What this is

Three Claude Code subagents and a bash loop that turn a requirements doc into committed backend code without supervision. The loop runs on Linux, macOS and Windows (via git-bash, which ships with Git for Windows).

| Piece | File | Role |
|---|---|---|
| `django-task-planner` | [.claude/agents/django-task-planner.md](../.claude/agents/django-task-planner.md) | Reads a requirements doc, writes `tasks.md` (numbered, small, ordered). Does **not** implement. |
| `django-task-runner` | [.claude/agents/django-task-runner.md](../.claude/agents/django-task-runner.md) | Picks the first `**Status**: pending` task, implements it end-to-end, verifies, commits, marks it done, stops. |
| `django-task-reviewer` | [.claude/agents/django-task-reviewer.md](../.claude/agents/django-task-reviewer.md) | Reads `git diff main...HEAD` + `tasks.md` + `progress/` and reports convention violations. Read-only. |
| `scripts/run-tasks.sh` | [scripts/run-tasks.sh](../scripts/run-tasks.sh) | Loops the runner one task at a time until `tasks.md` has no pending entries or the agent stalls `--max-stalled` times. |
| `scripts/format-stream.py` | [scripts/format-stream.py](../scripts/format-stream.py) | Reads `stream-json` events on stdin and prints a colored, human-readable transcript. Used live by `run-tasks.sh` and by `pretty-log.sh`. |
| `scripts/detect_quota.py` | [scripts/detect_quota.py](../scripts/detect_quota.py) | Scans an iteration's log chunk for Claude quota-exhaustion markers; tells `run-tasks.sh` whether the next iteration should sleep until reset (session) or abort (weekly). |

## State files

| File | Owned by | Purpose |
|---|---|---|
| `tasks.md` | planner (writes) / runner (flips status) | Backlog. Seeded from [tasks.md.example](../tasks.md.example). |
| `progress/T00N-done.md` | runner | One file per completed task: files touched, endpoints, migrations, non-obvious decisions, mocks. |
| `SETUP_REQUIRED.md` | runner | Human-blocked items (API keys, external config). Runner mocks the code path and appends here instead of halting. |
| `logs/run-tasks-*.log` | loop | Raw `stream-json` transcript of every iteration. Pretty-print with `just task-log <path>`. |

## End-to-end flow

```
requirements.md ──[planner]──> tasks.md
                                  │
                                  ▼
                       ┌─[just task-run]──────────────┐
                       │  loop: while pending tasks   │
                       │    runner picks first pending│
                       │    implements + verifies     │
                       │    commits on current branch │
                       │    writes progress/T00N.md   │
                       └──────────────────────────────┘
                                  │
                                  ▼
                          [just review] ──> logs/review.log
```

## Running it

```bash
# 1. Plan: invoke the planner interactively against a requirements doc.
#    (No just recipe — run from a Claude Code session.)
claude  # then: "Use the django-task-planner subagent to turn REQUIREMENTS.md into tasks.md"

# 2. Switch off main — the runner commits after every task.
git checkout -b claude-tasks

# 3. Run the loop.
just task-run            # equivalent to: bash scripts/run-tasks.sh

# 4. Review when the loop finishes (or stalls).
just review              # writes logs/review.log
```

The loop refuses to run on `main` / `master`. Requirements: `bash`, `git`, `python3`, and the `claude` CLI on `PATH` (or at `~/.local/bin/claude` — `claude.exe` is also accepted, for the git-bash setup on Windows). On Windows, install Git for Windows so `git-bash` is available; `just` picks it up via the shebang in the recipes.

## Conventions the runner enforces

The runner reads [AGENTS.md](../AGENTS.md) and [conventions.md](./conventions.md) on every invocation and additionally honors task-level skill references. The key rules it will not break unless a task says so verbatim:

- Object create/update logic lives in the serializer, not the view.
- Permissions in `permissions = {...}`, serializers in `serializers = {...}`.
- `BaseModel` / `BaseModelViewSet` inheritance; PUT stays disabled.
- No throttling, caching, signals, new middleware, Celery, Channels, S3, Sentry, or debug toolbar.
- One task = one commit on the current branch (never `--no-verify`, never amend).

See the agent file for the full list.

## When the loop stops

| Exit | Meaning | Action |
|---|---|---|
| `=== All tasks completed ===` | No `**Status**: pending` left in `tasks.md`. | Run `just review`. Address any `SETUP_REQUIRED.md` items. |
| `[x] Agent is not advancing tasks` | `--max-stalled` (default 3) iterations in a row produced no progress. | Inspect `tasks.md` and the latest `logs/run-tasks-*.log`. Likely causes: an `## Open questions` entry blocks the next task, a verification failed (`just lint` / `just test` / `just schema-validate`), or the task description is too vague. |
| Refuses to start on `main` | Safety guard. | `git checkout -b claude-tasks` and retry. |
| `claude CLI not found` | CLI not installed. | Install Claude Code, or symlink it under `~/.local/bin/`. |
| `[x] Weekly usage cap reached` | The Pro/Max weekly cap was hit. Nothing to wait for — the loop exits. | Resume in the next billing window. |
| `[x] Session resets in <s>s, exceeds --max-quota-wait` | A 5-hour reset would require waiting longer than the configured ceiling. | Re-run with a larger `--max-quota-wait` or kick off a fresh session manually. |

## Quota handling

The loop is designed to run overnight across multiple Pro/Max session windows.

- When Claude reports the **5-hour session window** as exhausted, the iteration is treated as a non-stall: the loop parses the reset timestamp from the log (`reset_at` epoch or `resets at <ISO>`) and sleeps until that moment plus a 60-second buffer. If no reset time can be parsed, it falls back to a 15-minute poll. The stall counter is not incremented.
- When Claude reports the **weekly cap** as reached, the loop exits with a clear message — there is no point in waiting.
- The maximum wait per quota event is capped by `--max-quota-wait` (default `43200` seconds = 12h). If the reset is further than that, the loop aborts instead of sleeping indefinitely.
- Detection lives in [scripts/detect_quota.py](../scripts/detect_quota.py). It matches case-insensitively on `usage limit reached`, `5-hour limit`, `weekly limit`, `claude_ai_usage_limit_reached`, `usage_limit_exceeded`. Tighten the regexes there when the CLI changes wording.

## Extending the workflow

- **Adding an agent**: drop it in `.claude/agents/`, add a recipe to `justfile`, and add a row to the table above.
- **Changing the loop**: edit [scripts/run-tasks.sh](../scripts/run-tasks.sh). The `--max-stalled`, `--max-turns`, and `--max-quota-wait` flags are the usual ones to tune.
- **Changing what "done" means**: edit the *Verification (Definition of Done)* section in [django-task-runner.md](../.claude/agents/django-task-runner.md). The reviewer checklist in [django-task-reviewer.md](../.claude/agents/django-task-reviewer.md) should change in lockstep.
