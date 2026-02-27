# Start realtime engine (LIVE) for 5 seconds then stop, and print latest log tail
$python = "C:/Users/Admin/trading-stockfish/.venv/Scripts/python.exe"
$cwd = "C:/Users/Admin/trading-stockfish"
# Stop any existing realtime processes
$matches = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'loop\\realtime.py' }
if ($matches) { $matches | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }
# Start
# Capture stdout/stderr to files so crash tracebacks are visible
$out = Join-Path $cwd 'logs\engine_out.log'
$err = Join-Path $cwd 'logs\engine_err.log'
$p = Start-Process -FilePath $python -ArgumentList 'loop/realtime.py --live' -WorkingDirectory $cwd -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow -PassThru
Write-Output "ENGINE_STARTED PID=$($p.Id)"
Start-Sleep -Seconds 5
if (-not $p.HasExited) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Write-Output "ENGINE_STOPPED PID=$($p.Id)"
} else {
    Write-Output "ENGINE_EXITED"
}
# Tail latest log
Start-Sleep -Seconds 1
$log = Get-ChildItem logs -Filter 'trading_engine_*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($null -eq $log) { Write-Output 'NO_LOG_FOUND'; exit 0 }
Write-Output "=== LOG START: $($log.FullName) ==="
Get-Content $log.FullName -Tail 200
Write-Output '=== LOG END ==='

Write-Output "=== STDOUT (engine_out.log) ==="
if (Test-Path $out) { Get-Content $out -Tail 200 } else { Write-Output 'NO_OUT_FILE' }
Write-Output "=== STDERR (engine_err.log) ==="
if (Test-Path $err) { Get-Content $err -Tail 400 } else { Write-Output 'NO_ERR_FILE' }