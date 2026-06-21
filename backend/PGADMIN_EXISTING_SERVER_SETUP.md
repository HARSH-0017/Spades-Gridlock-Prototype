# Using An Existing pgAdmin Server

pgAdmin is only the user interface. The project also needs a PostgreSQL server connection.

## 1. Check Whether pgAdmin Already Has A Server

Open pgAdmin and look at the left sidebar:

```text
Servers
  -> some server name
      -> Databases
```

If there is no server under `Servers`, PostgreSQL is not connected yet.

## 2. Get These Connection Details

From the registered server properties in pgAdmin:

- Host name/address
- Port, usually `5432`
- Maintenance database or target database
- Username
- Password

For a local install, common values are:

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gridlock
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
```

## 3. Create The `gridlock` Database

In pgAdmin Query Tool, connected as a superuser such as `postgres`, run:

```sql
CREATE DATABASE gridlock;
```

Then connect to the new `gridlock` database and run:

```sql
CREATE SCHEMA IF NOT EXISTS gridlock;
```

## 4. Update `.env`

Edit:

```text
E:\gridlock\theme 1\production\.env
```

Set the actual host, port, database, user, and password.

## 5. Test Connection

From PowerShell:

```powershell
cd 'E:\gridlock\theme 1\production'
.\scripts\test_connection.ps1
```

If this succeeds, run:

```powershell
.\scripts\setup_database.ps1
```

## 6. Inspect Tables In pgAdmin

After setup, refresh pgAdmin:

```text
Databases
  -> gridlock
      -> Schemas
          -> gridlock
              -> Tables
```

Useful query pack:

```text
db\pgadmin_queries.sql
```
