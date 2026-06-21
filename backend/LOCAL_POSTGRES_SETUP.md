# Local PostgreSQL + pgAdmin Setup

Use this if you want to run PostgreSQL locally on your machine.

## 1. Install PostgreSQL

Download the Windows installer from:

```text
https://www.postgresql.org/download/windows/
```

During install, include:

- PostgreSQL Server
- pgAdmin 4
- Command Line Tools

Remember the password you set for the `postgres` superuser.

## 2. Add PostgreSQL To PATH

Typical path:

```text
C:\Program Files\PostgreSQL\16\bin
```

After adding it, open a new PowerShell and check:

```powershell
psql --version
```

## 3. Create Database And User

Fast path from PowerShell:

```powershell
cd 'E:\gridlock\theme 1\production'
.\scripts\bootstrap_local_postgres.ps1
```

The script prompts securely for your PostgreSQL admin password and the password you want to set for `gridlock_app`.

Manual path: open SQL Shell or pgAdmin Query Tool as user `postgres`, then run:

```sql
CREATE DATABASE gridlock;
CREATE USER gridlock_app WITH PASSWORD 'change_me_strong_password';
GRANT ALL PRIVILEGES ON DATABASE gridlock TO gridlock_app;
```

Then connect to database `gridlock` and run:

```sql
CREATE SCHEMA IF NOT EXISTS gridlock AUTHORIZATION gridlock_app;
GRANT ALL ON SCHEMA gridlock TO gridlock_app;
```

## 4. Configure `.env`

In `E:\gridlock\theme 1\production\.env`:

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gridlock
POSTGRES_USER=gridlock_app
POSTGRES_PASSWORD=change_me_strong_password
```

## 5. Run Setup

```powershell
cd 'E:\gridlock\theme 1\production'
.\scripts\setup_database.ps1
```

## 6. Open pgAdmin

Open pgAdmin 4 from the Start menu and register a server:

- Host: `localhost`
- Port: `5432`
- Database: `gridlock`
- User: `gridlock_app`
- Password: value from `.env`
