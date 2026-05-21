# Task loop runner. Picks pending tasks from tasks.md, invokes the
# django-task-runner subagent on each, stops when no pending remain or
# when the agent makes no progress N times in a row.
#
# Usage:
#   pwsh -NoProfile -File scripts/run-tasks.ps1
#   pwsh -NoProfile -File scripts/run-tasks.ps1 -MaxStalled 5
#
# Wired through justfile as `just task-run`.

param(
    [string]$TasksFile = "tasks.md",
    [int]$MaxStalled = 3,
    [int]$MaxTurns = 80
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot/format-stream.ps1"

function Count-Pending {
    if (-not (Test-Path $TasksFile)) { return 0 }
    $matches = Select-String -Path $TasksFile -Pattern "^\*\*Status\*\*: pending" -ErrorAction SilentlyContinue
    if ($matches) { return @($matches).Count } else { return 0 }
}

function Report-Setup {
    if (-not (Test-Path "SETUP_REQUIRED.md")) { return }
    $matches = Select-String -Path "SETUP_REQUIRED.md" -Pattern "^- \[ \]" -ErrorAction SilentlyContinue
    $count = if ($matches) { @($matches).Count } else { 0 }
    if ($count -gt 0) {
        Write-Host ""
        Write-Host "[!] $count item(s) in SETUP_REQUIRED.md still need manual configuration." -ForegroundColor Yellow
    }
}

if (-not (Test-Path $TasksFile)) {
    Write-Error "ERROR: $TasksFile not found. Copy tasks.md.example to tasks.md and fill it in."
    exit 1
}

# Refuse to run on the protected branches. The builder commits after every task,
# so we don't want it polluting main/master. Check out a dedicated branch first
# (convention in this repo: `claude-tasks`).
$currentBranch = (& git rev-parse --abbrev-ref HEAD 2>$null).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($currentBranch)) {
    Write-Error "ERROR: could not detect current git branch (not a git repo, or detached HEAD)."
    exit 1
}
if ($currentBranch -in @('main', 'master')) {
    Write-Error "ERROR: refusing to run on '$currentBranch'. The builder will commit after every task. Run 'git checkout -b claude-tasks' (or pick another branch) and retry."
    exit 1
}

$claudeExe = Get-Command claude -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $claudeExe) {
    $fallback = "$env:USERPROFILE\.local\bin\claude.exe"
    if (Test-Path $fallback) {
        $env:PATH = "$env:PATH;$env:USERPROFILE\.local\bin"
        $claudeExe = $fallback
    }
    else {
        Write-Error "ERROR: claude CLI not found on PATH nor at $fallback"
        exit 1
    }
}

if (-not (Test-Path logs)) { New-Item -ItemType Directory logs | Out-Null }
$runLog = "logs/run-tasks-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date)

Write-Host "=== Task Runner ===" -ForegroundColor Cyan
Write-Host "tasks file:  $TasksFile"
Write-Host "log:         $runLog"
Write-Host "pending:     $(Count-Pending)"
Write-Host ""

$stalled = 0
$iteration = 0

$prompt = "Use the Task tool with subagent_type=django-task-runner. Read tasks.md, pick the first task whose status is 'pending', implement it end-to-end per the agent's instructions, mark it done, write the progress note, and stop. Do not pick a second task."

# Escape for embedding in the inner pwsh -Command single-quoted string.
$promptEsc = $prompt -replace "'", "''"

while ((Count-Pending) -gt 0) {
    $iteration++
    $pendingBefore = Count-Pending

    Write-Host ""
    Write-Host ">> Iteration $iteration ($pendingBefore pending)" -ForegroundColor Cyan

    "" | Add-Content $runLog
    "=== Iteration $iteration @ $(Get-Date -Format o) ($pendingBefore pending) ===" | Add-Content $runLog

    $innerCmd = "& claude -p --output-format stream-json --verbose --include-partial-messages --max-turns $MaxTurns '$promptEsc'"
    # Raw JSONL goes to the log (audit); each line is also pretty-printed live to the host.
    pwsh -NoProfile -Command $innerCmd 2>&1 | ForEach-Object {
        $_ | Add-Content -Path $runLog
        Format-StreamEvent $_
    }

    $pendingAfter = Count-Pending

    if ($pendingAfter -ge $pendingBefore) {
        $stalled++
        Write-Host "[!] No progress ($pendingAfter still pending). Stall $stalled/$MaxStalled" -ForegroundColor Yellow
        if ($stalled -ge $MaxStalled) {
            Write-Host "[x] Agent is not advancing tasks. Inspect $TasksFile and $runLog." -ForegroundColor Red
            Report-Setup
            exit 1
        }
    }
    else {
        $stalled = 0
        Write-Host "[ok] Task completed ($pendingBefore -> $pendingAfter pending)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== All tasks completed ===" -ForegroundColor Green
Report-Setup
