import os
import subprocess
import sys
import threading
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from db import fetch_all


app = FastAPI(title="GridLock Parking Intelligence API", version="1.0.0")
BACKEND_DIR = Path(__file__).resolve().parents[1]
PRODUCTION_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PRODUCTION_DIR / "frontend"
REACT_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")
TRAINING_SCRIPT = BACKEND_DIR / "src" / "train_ml_hotspot_model.py"

allowed_origins = [origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if REACT_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=REACT_DIST_DIR / "assets"), name="react-assets")

retrain_lock = threading.Lock()
retrain_status = {
    "state": "idle",
    "started_at": None,
    "finished_at": None,
    "last_success_at": None,
    "last_error": "",
    "last_output": "",
}


def json_ready(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def rows(sql, params=None):
    return [{key: json_ready(value) for key, value in row.items()} for row in fetch_all(sql, params)]


def latest_model_snapshot():
    try:
        result = rows(
            """
            SELECT model_version, trained_at
            FROM gridlock.ml_model_metrics
            ORDER BY trained_at DESC
            LIMIT 1
            """
        )
        return result[0] if result else {}
    except Exception as exc:
        return {"lookup_error": str(exc)}


def get_retrain_status_payload():
    with retrain_lock:
        payload = dict(retrain_status)
    payload["latest_model"] = latest_model_snapshot()
    return payload


def update_retrain_status(**changes):
    with retrain_lock:
        retrain_status.update(changes)


def run_retrain_job():
    started_at = datetime.utcnow().isoformat() + "Z"
    update_retrain_status(
        state="running",
        started_at=started_at,
        finished_at=None,
        last_error="",
        last_output="",
    )

    try:
        completed = subprocess.run(
            [sys.executable, str(TRAINING_SCRIPT)],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        finished_at = datetime.utcnow().isoformat() + "Z"
        output = "\n".join(
            line
            for line in [completed.stdout.strip(), completed.stderr.strip()]
            if line
        ).strip()
        output_tail = "\n".join(output.splitlines()[-20:]) if output else ""

        if completed.returncode != 0:
            update_retrain_status(
                state="failed",
                finished_at=finished_at,
                last_error=output_tail or f"Training exited with code {completed.returncode}.",
                last_output=output_tail,
            )
            return

        update_retrain_status(
            state="completed",
            finished_at=finished_at,
            last_success_at=finished_at,
            last_error="",
            last_output=output_tail,
        )
    except Exception as exc:
        finished_at = datetime.utcnow().isoformat() + "Z"
        update_retrain_status(
            state="failed",
            finished_at=finished_at,
            last_error=str(exc),
            last_output="",
        )


@app.get("/", include_in_schema=False)
def dashboard():
    react_index = REACT_DIST_DIR / "index.html"
    if react_index.exists():
        return FileResponse(react_index)
    return HTMLResponse(
        "<h1>Frontend build not found</h1><p>Run backend/scripts/build_frontend.ps1 to build the React app.</p>",
        status_code=503,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admin/retrain-status")
def admin_retrain_status():
    return get_retrain_status_payload()


@app.post("/admin/retrain-model")
def admin_retrain_model():
    should_start = False
    with retrain_lock:
        if retrain_status["state"] in {"starting", "running"}:
            raise HTTPException(status_code=409, detail="Model retraining is already running.")
        retrain_status.update(
            {
                "state": "starting",
                "started_at": datetime.utcnow().isoformat() + "Z",
                "finished_at": None,
                "last_error": "",
                "last_output": "",
            }
        )
        should_start = True

    if should_start:
        worker = threading.Thread(target=run_retrain_job, daemon=True)
        worker.start()

    return {
        "message": "Model retraining started.",
        "status": get_retrain_status_payload(),
    }


@app.get("/summary")
def summary():
    result = rows(
        """
        SELECT
            (SELECT COUNT(*) FROM gridlock.parking_violations_raw) AS raw_records,
            (SELECT COUNT(*) FROM gridlock.hotspot_areas) AS hotspot_areas,
            (SELECT COUNT(*) FROM gridlock.hotspot_cells) AS hotspot_cells,
            (SELECT COUNT(*) FROM gridlock.next_day_deployment_plan WHERE deployment_status = 'Deploy') AS deploy_count,
            (SELECT COALESCE(SUM(suggested_patrol_units), 0) FROM gridlock.next_day_deployment_plan WHERE deployment_status <> 'Monitor') AS suggested_units,
            (SELECT MAX(operational_impact_score_0_100) FROM gridlock.hotspot_areas) AS top_impact_score,
            (SELECT MAX(target_date) FROM gridlock.next_day_deployment_plan) AS target_date
        """
    )
    return result[0]


@app.get("/hotspot-areas")
def hotspot_areas(
    station: str | None = None,
    limit: int = 25,
):
    limit = max(1, min(int(limit), 200))
    params = []
    where = ""
    if station:
        where = "WHERE primary_police_station = %s"
        params.append(station)
    params.append(limit)
    return rows(
        f"""
        SELECT *
        FROM gridlock.hotspot_areas
        {where}
        ORDER BY operational_impact_score_0_100 DESC, records DESC
        LIMIT %s
        """,
        params,
    )


@app.get("/deployment-plan")
def deployment_plan(target_date: str | None = None):
    if target_date:
        return rows(
            """
            SELECT *
            FROM gridlock.next_day_deployment_plan
            WHERE target_date = %s
            ORDER BY
                CASE deployment_status
                    WHEN 'Deploy' THEN 1
                    WHEN 'Targeted patrol' THEN 2
                    ELSE 3
                END,
                operational_impact_score_0_100 DESC
            """,
            [target_date],
        )
    return rows(
        """
        SELECT *
        FROM gridlock.next_day_deployment_plan
        ORDER BY target_date DESC, operational_impact_score_0_100 DESC
        LIMIT 200
        """
    )


@app.get("/station-load")
def station_load(limit: int = 20):
    limit = max(1, min(int(limit), 100))
    return rows(
        """
        SELECT police_station, COUNT(*) AS records
        FROM gridlock.parking_violations_raw
        GROUP BY police_station
        ORDER BY records DESC
        LIMIT %s
        """,
        [limit],
    )


@app.get("/action-plan")
def action_plan(limit: int = 40):
    limit = max(1, min(int(limit), 200))
    return rows(
        """
        SELECT *
        FROM gridlock.enforcement_action_plan
        ORDER BY
            CASE priority_band
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                ELSE 4
            END,
            operational_impact_score_0_100 DESC
        LIMIT %s
        """,
        [limit],
    )


@app.get("/hourly-load")
def hourly_load():
    return rows(
        """
        SELECT
            LPAD(hour_ist::text, 2, '0') || ':00-' || LPAD(hour_ist::text, 2, '0') || ':59' AS time_window_ist,
            records
        FROM gridlock.v_hourly_city_load
        ORDER BY records DESC
        """
    )


@app.get("/station-shift-plan")
def station_shift_plan(limit: int = 50):
    limit = max(1, min(int(limit), 200))
    return rows(
        """
        SELECT
            primary_police_station,
            recommended_time_window_ist,
            COUNT(*) AS priority_area_count,
            SUM(historical_area_records) AS covered_records,
            SUM(suggested_patrol_units) AS suggested_patrol_units
        FROM gridlock.next_day_deployment_plan
        WHERE deployment_status <> 'Monitor'
        GROUP BY primary_police_station, recommended_time_window_ist
        ORDER BY suggested_patrol_units DESC, covered_records DESC
        LIMIT %s
        """,
        [limit],
    )


@app.get("/violation-mix")
def violation_mix(limit: int = 12):
    limit = max(1, min(int(limit), 50))
    return rows(
        """
        SELECT label AS violation_label, COUNT(*) AS records
        FROM gridlock.parking_violations_raw,
             jsonb_array_elements_text(violation_type) AS label
        GROUP BY label
        ORDER BY records DESC
        LIMIT %s
        """,
        [limit],
    )


@app.get("/validation-metrics")
def validation_metrics():
    result = rows(
        """
        SELECT
            precision_at_10,
            precision_at_20,
            precision_at_50,
            recall_at_50,
            roc_auc,
            log_loss,
            notes AS note
        FROM gridlock.ml_model_metrics
        ORDER BY trained_at DESC
        LIMIT 1
        """
    )
    if result:
        result[0]["top_50_holdout_capture_share"] = result[0]["recall_at_50"]
        return result[0]
    return {
        "precision_at_10": 0.0,
        "precision_at_20": 0.0,
        "precision_at_50": 0.0,
        "recall_at_50": 0.0,
        "roc_auc": 0.0,
        "log_loss": 0.0,
        "top_50_holdout_capture_share": 0.0,
        "note": "ML model has not been trained yet. Run src/train_ml_hotspot_model.py.",
    }


@app.get("/ml-metrics")
def ml_metrics():
    result = rows(
        """
        SELECT *
        FROM gridlock.ml_model_metrics
        ORDER BY trained_at DESC
        LIMIT 1
        """
    )
    return result[0] if result else {}


@app.get("/ml-predictions")
def ml_predictions(limit: int = 20):
    limit = max(1, min(int(limit), 100))
    return rows(
        """
        SELECT *
        FROM gridlock.ml_hotspot_predictions
        WHERE model_version = (
            SELECT model_version
            FROM gridlock.ml_model_metrics
            ORDER BY trained_at DESC
            LIMIT 1
        )
        ORDER BY target_date DESC, ml_risk_probability DESC, predicted_next_day_records DESC
        LIMIT %s
        """,
        [limit],
    )


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    react_index = REACT_DIST_DIR / "index.html"
    if react_index.exists():
        return FileResponse(react_index)
    return HTMLResponse(
        "<h1>Frontend build not found</h1><p>Run frontend build before opening app routes.</p>",
        status_code=503,
    )
