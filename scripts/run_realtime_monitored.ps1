# Run realtime engine in short monitored iterations to surface issues quickly
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run_realtime_monitored.ps1

$python = "C:/Users/Admin/trading-stockfish/.venv/Scripts/python.exe"
$cwd = "C:/Users/Admin/trading-stockfish"

# Number of iterations and sleep per iteration (total ~= ITERATIONS * SLEEP)
$iterations = 5
$sleepSec = 60

function Stop-ExistingRealtime {
    $matches = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'loop\\realtime.py' }
    if ($matches) { $matches | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }
}

function Tail-Logs {
    $log = Get-ChildItem "$cwd/logs" -Filter 'trading_engine_*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -eq $log) { Write-Output 'NO_LOG_FOUND'; return }
    Write-Output "=== LOG TAIL START: $($log.FullName) ==="
    Get-Content $log.FullName -Tail 200
    Write-Output "=== LOG TAIL END ==="
    $out = Join-Path $cwd 'logs\engine_out.log'
    $err = Join-Path $cwd 'logs\engine_err.log'
    Write-Output '=== STDOUT (engine_out.log) ==='
    if (Test-Path $out) { Get-Content $out -Tail 200 } else { Write-Output 'NO_OUT_FILE' }
    Write-Output '=== STDERR (engine_err.log) ==='
    if (Test-Path $err) { Get-Content $err -Tail 400 } else { Write-Output 'NO_ERR_FILE' }
}

Push-Location $cwd
Stop-ExistingRealtime

for ($i = 1; $i -le $iterations; $i++) {
    Write-Output ("--- ITERATION {0}/{1}: starting engine PID ---" -f $i, $iterations)
    $p = Start-Process -FilePath $python -ArgumentList 'loop/realtime.py --live' -WorkingDirectory $cwd -PassThru
    Write-Output "ENGINE_STARTED PID=$($p.Id)"
    Start-Sleep -Seconds $sleepSec
    if (-not $p.HasExited) {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        Write-Output "ENGINE_STOPPED PID=$($p.Id)"
    } else {
        Write-Output "ENGINE_PROCESS_EXITED"
    }

    # Small grace before reading logs
    Start-Sleep -Seconds 1
    Tail-Logs

    # Quick heuristic: if last log tail contains no WARNING/ERROR lines, we can stop early
    $log = Get-ChildItem "$cwd/logs" -Filter 'trading_engine_*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -ne $log) {
        $snippet = Get-Content $log.FullName -Tail 200 | Select-String -Pattern 'WARNING|ERROR' -SimpleMatch
        if ($snippet -eq $null) {
            Write-Output ("No WARNING/ERROR in recent logs - stopping early (iteration {0})" -f $i)
            Break
        } else {
            Write-Output "Found WARNING/ERROR in recent logs - continuing to next iteration"
        }
    }
}

Stop-ExistingRealtime
Pop-Location
