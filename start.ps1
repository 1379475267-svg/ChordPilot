$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Backend virtual environment was not found. Install backend dependencies first."
}

if (-not (Test-Path -LiteralPath (Join-Path $frontend "node_modules"))) {
    throw "Frontend dependencies were not found. Run npm install in the frontend directory first."
}

$backendRunning = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$frontendRunning = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

if (-not $backendRunning) {
    Start-Process powershell -WorkingDirectory $backend -ArgumentList @(
        "-NoExit",
        "-Command",
        "& `"$python`" -m uvicorn main:app --reload --port 8000"
    )
}

if (-not $frontendRunning) {
    Start-Process powershell -WorkingDirectory $frontend -ArgumentList @(
        "-NoExit",
        "-Command",
        "npm run dev"
    )
}

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host "ChordPilot is running at http://localhost:5173" -ForegroundColor Green
