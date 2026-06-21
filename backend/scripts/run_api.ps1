$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { $BundledPython }

Push-Location $Root
try {
    if (!(Test-Path $Python)) {
        throw "Python was not found. Checked: $VenvPython and $BundledPython"
    }

    & $Python -m uvicorn api:app --app-dir src --host 0.0.0.0 --port 8000
}
finally {
    Pop-Location
}
