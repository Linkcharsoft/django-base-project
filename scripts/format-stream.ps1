# Dot-sourceable helper. Defines Format-StreamEvent, which converts a single
# stream-json line from `claude -p --output-format stream-json` into a human-
# readable line printed to the host. Returns nothing.
#
# Usage from another script:
#   . "$PSScriptRoot/format-stream.ps1"
#   Get-Content $log | ForEach-Object { Format-StreamEvent $_ }

function Format-StreamEvent {
    param([string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) { return }

    try {
        $evt = $Line | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Write-Host $Line
        return
    }

    switch ($evt.type) {
        'system' {
            if ($evt.subtype -eq 'init') {
                Write-Host "[init] session $($evt.session_id)" -ForegroundColor DarkGray
            }
        }
        'assistant' {
            foreach ($block in $evt.message.content) {
                switch ($block.type) {
                    'text' {
                        if ($block.text) { Write-Host $block.text }
                    }
                    'tool_use' {
                        $name = $block.name
                        $brief = ''
                        if ($block.input) {
                            $fields = @('file_path', 'path', 'command', 'pattern', 'description', 'subagent_type', 'prompt')
                            foreach ($f in $fields) {
                                $val = $block.input.$f
                                if ($val) {
                                    $s = "$val"
                                    if ($s.Length -gt 140) { $s = $s.Substring(0, 137) + '...' }
                                    $brief = "$f=$s"
                                    break
                                }
                            }
                        }
                        Write-Host "  -> $name $brief" -ForegroundColor Cyan
                    }
                }
            }
        }
        'user' {
            foreach ($block in $evt.message.content) {
                if ($block.type -eq 'tool_result') {
                    $content = "$($block.content)"
                    if ($content.Length -gt 200) { $content = $content.Substring(0, 197) + '...' }
                    $color = if ($block.is_error) { 'Red' } else { 'DarkGray' }
                    Write-Host "  <- $content" -ForegroundColor $color
                }
            }
        }
        'result' {
            Write-Host ""
            Write-Host "=== RESULT ($($evt.subtype)) ===" -ForegroundColor Green
            if ($evt.result) { Write-Host $evt.result }
            if ($evt.total_cost_usd) {
                $cost = [math]::Round($evt.total_cost_usd, 4)
                $dur = [math]::Round($evt.duration_ms / 1000, 1)
                Write-Host "cost: `$$cost  duration: ${dur}s" -ForegroundColor DarkGray
            }
            Write-Host ""
        }
    }
}
