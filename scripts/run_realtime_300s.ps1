# Starts the realtime engine (LIVE) for 300 seconds, then stops it.
# Usage: powershell -File scripts\run_realtime_300s.ps1

$python = "C:/Users/Admin/trading-stockfish/.venv/Scripts/python.exe"
$cwd = "C:/Users/Admin/trading-stockfish"

# Stop any existing realtime.py processes
$matches = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'loop\\realtime.py' }
if ($matches) { $matches | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }

# Start realtime engine in LIVE mode
$p = Start-Process -FilePath $python -ArgumentList 'loop/realtime.py --live' -WorkingDirectory $cwd -PassThru
Write-Output "ENGINE_STARTED PID=$($p.Id)"

# Run for 300 seconds
Start-Sleep -Seconds 300

# Stop process if still running
if (-not $p.HasExited) {
    try {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        Write-Output "ENGINE_STOPPED PID=$($p.Id)"
    } catch {
        Write-Output "ENGINE_STOP_STOP_FAILED"
    }
} else {
    Write-Output "ENGINE_PROCESS_EXITED"
}
