# Production Workspace

The `production` workspace is now split cleanly into two apps:

- `backend/` - PostgreSQL schema, ingestion scripts, FastAPI service, and backend setup docs
- `frontend/` - React dashboard source, build output, and frontend dependencies

Deployment target:

- `backend/` -> Render
- `frontend/` -> Vercel

## Common Paths

- Backend README: `backend/README.md`
- Backend scripts: `backend/scripts`
- FastAPI source: `backend/src`
- React app source: `frontend/src`

## Typical Workflow

1. Open `backend/` to set up PostgreSQL, ingest data, and run the API.
2. Use `backend/scripts/build_frontend.ps1` to build the React app from `frontend/`.
3. Start the API with `backend/scripts/run_api.ps1` to serve the dashboard at `http://127.0.0.1:8000/`.

## Note

If you moved this project from the older `frontend-react` layout, reinstall frontend dependencies once inside `frontend/` before rebuilding the app. The existing `dist/` output is still available for the API to serve.
