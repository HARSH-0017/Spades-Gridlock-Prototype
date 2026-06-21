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

    & $Python -m pip install -r requirements.txt
    & $Python src/test_connection.py
}
finally {
    Pop-Location
}
