# Wait for latest trading_engine log file and tail it
# Usage: powershell -File scripts\tail_latest_log.ps1

# Wait until a matching log appears
while (-not (Get-ChildItem logs -Filter 'trading_engine_*.log' -ErrorAction SilentlyContinue)) {
    Start-Sleep -Seconds 1
}

$log = Get-ChildItem logs -Filter 'trading_engine_*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Output "Tailing: $($log.FullName) -- start"

# Tail continuously
Get-Content $log.FullName -Tail 200 -Wait
