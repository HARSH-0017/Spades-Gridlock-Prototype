# GridLock Theme 1 Backend

This folder contains the backend for the Theme 1 parking-intelligence work. The React frontend now lives in the sibling `../frontend` folder.

The backend now keeps its own local copies of:

- source data in `data/`
- analytics artifacts in `outputs/`

## What This Adds

- PostgreSQL schema for raw violations, hotspot cells, hotspot areas, action plans, deployment plans, and field interventions.
- Idempotent CSV ingestion into PostgreSQL.
- Analytics-output loading into PostgreSQL.
- FastAPI service for dashboards or external systems.
- Field intervention table for real operational feedback.

## Architecture

```text
CSV source
  -> PostgreSQL raw table
  -> analytics pipeline
  -> hotspot/action/deployment marts in PostgreSQL
  -> API / dashboard / field feedback loop
```

## Recommended Deployment

- Backend API: Render
- Frontend app: Vercel
- Database: Render PostgreSQL or another managed PostgreSQL instance

For local development, use a normal PostgreSQL server and point `.env` at it.

## Local PostgreSQL Setup

If you want a local backend environment:

- Install PostgreSQL locally and follow `LOCAL_POSTGRES_SETUP.md`, or
- Use an already running PostgreSQL instance and follow `PGADMIN_EXISTING_SERVER_SETUP.md`

For a locally installed PostgreSQL server, run:

```powershell
.\scripts\create_database.ps1
.\scripts\setup_database.ps1
```

If you already have a PostgreSQL server and use pgAdmin to inspect it, follow:

```text
PGADMIN_EXISTING_SERVER_SETUP.md
```

## Check Prerequisites

```powershell
.\scripts\check_prerequisites.ps1
```

To verify that `.env` can reach PostgreSQL:

```powershell
.\scripts\test_connection.ps1
```

To create the database from `.env` without any prompts:

```powershell
.\scripts\create_database.ps1
```

## Install Python Dependencies

```powershell
& (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe') -m pip install -r requirements.txt
```

## Run Full Database Setup

After PostgreSQL is running:

```powershell
.\scripts\setup_database.ps1
```

This applies schema, ingests the raw CSV, runs the analytics pipeline, and loads analytics outputs into PostgreSQL.

## Run API

```powershell
.\scripts\run_api.ps1
```

API docs:

```text
http://localhost:8000/docs
```

Useful endpoints:

- `GET /health`
- `GET /hotspot-areas`
- `GET /hotspot-areas?station=Shivajinagar`
- `GET /deployment-plan`
- `GET /station-load`

## Build React Frontend

```powershell
.\scripts\build_frontend.ps1
.\scripts\run_api.ps1
```

This script builds the sibling frontend app in `../frontend`. The live React dashboard is served by the API at:

```text
http://127.0.0.1:8000/
```

## pgAdmin Query Pack

Use these ready-made SQL checks in pgAdmin:

```text
db/pgadmin_queries.sql
```

## Production Notes

- Change all passwords in `.env`.
- Use a managed PostgreSQL instance for Render deployment.
- Add scheduled ingestion when daily violation feeds are available.
- Keep `field_interventions` updated from field teams to measure before/after impact.
- Add traffic-speed, queue length, road class, and lane-capacity data before claiming measured congestion reduction.
