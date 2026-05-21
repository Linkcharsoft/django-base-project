# Pretty-print a stream-json log produced by run-tasks.ps1 (or any
# `claude -p --output-format stream-json` invocation).
#
# Usage:
#   pwsh -NoProfile -File scripts/pretty-log.ps1 -Path logs/run-tasks-20260521-144237.log
#   just task-log logs/run-tasks-20260521-144237.log

param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [switch]$Follow
)

if (-not (Test-Path $Path)) {
    Write-Error "Log not found: $Path"
    exit 1
}

. "$PSScriptRoot/format-stream.ps1"

if ($Follow) {
    Get-Content -Path $Path -Wait | ForEach-Object { Format-StreamEvent $_ }
}
else {
    Get-Content -Path $Path | ForEach-Object { Format-StreamEvent $_ }
}
