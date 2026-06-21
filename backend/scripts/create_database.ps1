$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { $BundledPython }

Push-Location $Root
try {
    if (!(Test-Path $Python)) {
        throw "Python was not found. Checked: $VenvPython and $BundledPython"
    }

    if (!(Test-Path ".env")) {
        throw "Missing .env file. Run: Copy-Item .env.example .env"
    }

    & $Python src/create_database_from_env.py
}
finally {
    Pop-Location
}
