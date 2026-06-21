$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { $BundledPython }

Write-Host "GridLock prerequisite check" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $Python) {
    Write-Host "[OK] Python found: $Python" -ForegroundColor Green
} else {
    Write-Host "[MISSING] Python not found. Checked: $VenvPython and $BundledPython" -ForegroundColor Red
}

$psql = Get-Command psql -ErrorAction SilentlyContinue
if ($psql) {
    Write-Host "[OK] psql found: $($psql.Source)" -ForegroundColor Green
} elseif (Test-Path "C:\Program Files\PostgreSQL\18\bin\psql.exe") {
    Write-Host "[OK] psql found at C:\Program Files\PostgreSQL\18\bin\psql.exe, but not in this shell's PATH" -ForegroundColor Green
} else {
    Write-Host "[INFO] psql not found in PATH. Local PostgreSQL tools are not available from this shell." -ForegroundColor Yellow
}

Push-Location $Root
try {
    if (Test-Path ".env") {
        Write-Host "[OK] .env exists" -ForegroundColor Green
    } else {
        Write-Host "[MISSING] .env does not exist. Run: Copy-Item .env.example .env" -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}
