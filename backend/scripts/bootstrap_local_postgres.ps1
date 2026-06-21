$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Psql = "psql"
$DefaultPsql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

function Invoke-PsqlChecked {
    param ([string[]] $PsqlArgs)

    & $Psql @PsqlArgs
    if ($LASTEXITCODE -ne 0) {
        throw "psql command failed. Check the PostgreSQL username/password and try again."
    }
}

if (!(Get-Command $Psql -ErrorAction SilentlyContinue)) {
    if (Test-Path $DefaultPsql) {
        $Psql = $DefaultPsql
    } else {
        throw "psql was not found in PATH and not found at $DefaultPsql"
    }
}

Push-Location $Root
try {
    if (!(Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example" -ForegroundColor Green
    }

    $adminUser = Read-Host "PostgreSQL admin user" 
    if ([string]::IsNullOrWhiteSpace($adminUser)) { $adminUser = "postgres" }

    $adminPasswordSecure = Read-Host "Password for PostgreSQL admin user '$adminUser'" -AsSecureString
    $adminPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPasswordSecure)
    )

    $appPasswordSecure = Read-Host "Password to set for gridlock_app" -AsSecureString
    $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($appPasswordSecure)
    )
    $escapedAppPassword = $appPassword.Replace("'", "''")

    $env:PGPASSWORD = $adminPassword

    Write-Host "Testing admin connection..." -ForegroundColor Cyan
    Invoke-PsqlChecked @(
        "-h", "localhost",
        "-p", "5432",
        "-U", $adminUser,
        "-d", "postgres",
        "--set=ON_ERROR_STOP=1",
        "-c", "SELECT current_user;"
    )

    Write-Host "Creating/updating role gridlock_app..." -ForegroundColor Cyan
    Invoke-PsqlChecked @(
        "-h", "localhost",
        "-p", "5432",
        "-U", $adminUser,
        "-d", "postgres",
        "--set=ON_ERROR_STOP=1",
        "-c", "DO `$`$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gridlock_app') THEN CREATE ROLE gridlock_app LOGIN PASSWORD '$escapedAppPassword'; ELSE ALTER ROLE gridlock_app WITH LOGIN PASSWORD '$escapedAppPassword'; END IF; END `$`$;"
    )

    Write-Host "Creating database gridlock if needed..." -ForegroundColor Cyan
    $dbExists = & $Psql @(
        "-h", "localhost",
        "-p", "5432",
        "-U", $adminUser,
        "-d", "postgres",
        "-t",
        "-A",
        "-c", "SELECT 1 FROM pg_database WHERE datname = 'gridlock';"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Could not check whether database gridlock exists. Check the PostgreSQL username/password and try again."
    }
    if (($null -eq $dbExists) -or ($dbExists.Trim() -ne "1")) {
        Invoke-PsqlChecked @(
            "-h", "localhost",
            "-p", "5432",
            "-U", $adminUser,
            "-d", "postgres",
            "--set=ON_ERROR_STOP=1",
            "-c", "CREATE DATABASE gridlock OWNER gridlock_app;"
        )
    } else {
        Write-Host "Database gridlock already exists." -ForegroundColor Yellow
    }

    Write-Host "Granting schema/database privileges..." -ForegroundColor Cyan
    Invoke-PsqlChecked @(
        "-h", "localhost",
        "-p", "5432",
        "-U", $adminUser,
        "-d", "gridlock",
        "--set=ON_ERROR_STOP=1",
        "-c", "CREATE SCHEMA IF NOT EXISTS gridlock AUTHORIZATION gridlock_app; GRANT ALL PRIVILEGES ON DATABASE gridlock TO gridlock_app; GRANT ALL ON SCHEMA gridlock TO gridlock_app;"
    )

    $envContent = @"
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gridlock
POSTGRES_USER=gridlock_app
POSTGRES_PASSWORD=$appPassword

PGADMIN_DEFAULT_EMAIL=admin@gridlock.local
PGADMIN_DEFAULT_PASSWORD=change_me_admin_password

SOURCE_CSV=data/jan to may police violation_anonymized791b166.csv
OUTPUT_DIR=outputs
"@
    Set-Content -LiteralPath ".env" -Value $envContent -Encoding UTF8
    Write-Host "Updated .env for gridlock_app." -ForegroundColor Green
    Write-Host "Bootstrap complete. Now run: .\scripts\setup_database.ps1" -ForegroundColor Green
}
finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    Pop-Location
}
