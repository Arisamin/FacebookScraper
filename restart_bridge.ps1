# ==============================================================================
# restart_bridge.ps1 - Restart FacebookScraper FastAPI Bridge & Worker Processes
# ==============================================================================

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "Stopping existing FacebookScraper Bridge & browser tasks..." -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# 1. Kill any process listening on port 8000 (FastAPI Bridge)
$port8000Pids = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique

if ($port8000Pids) {
    foreach ($targetPid in $port8000Pids) {
        try {
            $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "  -> Terminating process on port 8000: $($proc.ProcessName) (PID: $targetPid)" -ForegroundColor Yellow
                Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Host "  -> Could not stop PID $targetPid : $_" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "  -> No active process found listening on port 8000." -ForegroundColor Gray
}

# 2. Kill any lingering Uvicorn / Bridge Python processes matching the module name
$pyProcs = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" -ErrorAction SilentlyContinue
foreach ($p in $pyProcs) {
    if ($p.CommandLine -and ($p.CommandLine -like "*src.n8n_bridge.server*" -or $p.CommandLine -like "*uvicorn*")) {
        Write-Host "  -> Terminating bridge worker: PID $($p.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 3. Give OS 1.5 seconds to release network sockets
Start-Sleep -Milliseconds 1500

Write-Host "`nStarting fresh FastAPI Bridge server (with auto-reload)..." -ForegroundColor Cyan
$repoRoot = $PSScriptRoot
Set-Location $repoRoot

# Launch Uvicorn in a new PowerShell window so logs remain visible
$startArgs = "-m uvicorn src.n8n_bridge.server:app --host 0.0.0.0 --port 8000 --reload"
$newProc = Start-Process -FilePath "python" -ArgumentList $startArgs -PassThru

Write-Host "  -> Bridge launched with PID: $($newProc.Id)" -ForegroundColor Green

# 4. Health Check Probe (retry up to 5 times)
Write-Host "`nVerifying server health at http://127.0.0.1:8000/health..." -ForegroundColor Cyan
$healthy = $false
for ($i = 1; $i -le 6; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($response.status -eq "ok") {
            Write-Host "`n[SUCCESS] FacebookScraper Bridge is UP and HEALTHY!" -ForegroundColor Green
            Write-Host "Endpoint: http://127.0.0.1:8000" -ForegroundColor White
            Write-Host "Logs:     $repoRoot\logs\scraper.log`n" -ForegroundColor White
            $healthy = $true
            break
        }
    } catch {
        Write-Host "  [Attempt $i/6] Waiting for server startup..." -ForegroundColor DarkGray
    }
}

if (-not $healthy) {
    Write-Host "`n[WARNING] Bridge did not respond within 6 seconds. Check logs\scraper.log for details." -ForegroundColor Red
}
