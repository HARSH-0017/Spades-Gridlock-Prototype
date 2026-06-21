$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { $BundledPython }
$AnalysisOutputDir = Resolve-Path (Join-Path $Root "..\..\outputs")
$BackendOutputDir = Join-Path $Root "outputs"

Push-Location $Root
try {
    if (!(Test-Path $Python)) {
        throw "Python was not found. Checked: $VenvPython and $BundledPython"
    }

    if (!(Test-Path ".env")) {
        throw "Missing .env file. Run: Copy-Item .env.example .env"
    }

    $pgHost = (Select-String -Path ".env" -Pattern "^POSTGRES_HOST=" | Select-Object -First 1).Line -replace "^POSTGRES_HOST=", ""
    $pgPort = (Select-String -Path ".env" -Pattern "^POSTGRES_PORT=" | Select-Object -First 1).Line -replace "^POSTGRES_PORT=", ""
    if ([string]::IsNullOrWhiteSpace($pgHost)) { $pgHost = "localhost" }
    if ([string]::IsNullOrWhiteSpace($pgPort)) { $pgPort = "5432" }

    $canConnect = Test-NetConnection -ComputerName $pgHost -Port ([int]$pgPort) -InformationLevel Quiet
    if (-not $canConnect) {
        throw "PostgreSQL is not reachable at ${pgHost}:${pgPort}. Start PostgreSQL locally or point .env to your managed PostgreSQL instance before running this script."
    }

    & $Python -m pip install -r requirements.txt
    & $Python src/init_db.py
    & $Python src/ingest_parking_violations.py
    & $Python ..\..\analysis\00_run_pipeline.py
    New-Item -ItemType Directory -Force -Path $BackendOutputDir | Out-Null
    Copy-Item -Path (Join-Path $AnalysisOutputDir "*") -Destination $BackendOutputDir -Recurse -Force
    & $Python src/load_analytics_outputs.py
    & $Python src/train_ml_hotspot_model.py
}
finally {
    Pop-Location
}
