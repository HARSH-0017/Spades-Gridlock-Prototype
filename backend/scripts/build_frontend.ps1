$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RuntimeRoot = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies"
$Node = Join-Path $RuntimeRoot "node\bin\node.exe"
$Pnpm = Join-Path $RuntimeRoot "node\node_modules\pnpm\bin\pnpm.cjs"
$NodeBin = Join-Path $RuntimeRoot "node\bin"
$Frontend = Join-Path (Split-Path -Parent $Root) "frontend"

Push-Location $Frontend
try {
    if (!(Test-Path $Node)) {
        throw "Bundled Node.js was not found at $Node"
    }
    if (!(Test-Path $Pnpm)) {
        throw "pnpm was not found at $Pnpm"
    }

    $env:PATH = "$NodeBin;$env:PATH"
    $env:CI = "true"
    & $Node $Pnpm install --config.confirmModulesPurge=false --config.dangerouslyAllowAllBuilds=true
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend dependency install failed."
    }

    & $Node $Pnpm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed."
    }
}
finally {
    Pop-Location
}
