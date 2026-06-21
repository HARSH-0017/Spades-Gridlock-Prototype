import csv
from pathlib import Path

from psycopg2.extras import execute_values

from config import OUTPUT_DIR
from db import connect


def read_csv(name):
    path = OUTPUT_DIR / name
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def to_int(value):
    return int(float(value)) if value not in (None, "") else None


def to_float(value):
    return float(value) if value not in (None, "") else None


def load_hotspot_cells(cur):
    rows = read_csv("hotspot_priority_table.csv")
    cur.execute("TRUNCATE gridlock.hotspot_cells;")
    values = [
        (
            r["lat_cell"],
            r["lon_cell"],
            to_int(r["records"]),
            to_int(r["active_days"]),
            to_float(r["priority_score_0_100"]),
            r["police_station"],
            r["junction"],
            r["peak_hour_IST"],
            to_int(r["peak_hour_count"]),
            to_float(r["peak_hour_share"]),
            r["top_weekday"],
            to_float(r["avg_violation_severity_1_5"]),
            to_float(r["avg_vehicle_obstruction_1_5"]),
            r["top_violations"],
            r["top_vehicle_types"],
            r["sample_location"],
        )
        for r in rows
    ]
    execute_values(
        cur,
        """
        INSERT INTO gridlock.hotspot_cells (
            lat_cell, lon_cell, records, active_days, priority_score_0_100,
            police_station, junction, peak_hour_ist, peak_hour_count, peak_hour_share,
            top_weekday, avg_violation_severity_1_5, avg_vehicle_obstruction_1_5,
            top_violations, top_vehicle_types, sample_location
        ) VALUES %s
        """,
        values,
        page_size=5000,
    )


def load_hotspot_areas(cur):
    rows = read_csv("hotspot_area_priority_table.csv")
    cur.execute("TRUNCATE gridlock.hotspot_areas CASCADE;")
    values = [
        (
            to_int(r["area_rank"]),
            to_float(r["center_lat"]),
            to_float(r["center_lon"]),
            to_int(r["zone_count"]),
            to_int(r["records"]),
            to_int(r["max_active_days"]),
            to_float(r["area_priority_score_0_100"]),
            to_float(r["operational_impact_score_0_100"]),
            r["primary_police_station"],
            r["primary_junction"],
            r["recommended_time_window_IST"],
            r["top_violations"],
            r["top_vehicle_types"],
            r["representative_location"],
        )
        for r in rows
    ]
    execute_values(
        cur,
        """
        INSERT INTO gridlock.hotspot_areas (
            area_rank, center_lat, center_lon, zone_count, records, max_active_days,
            area_priority_score_0_100, operational_impact_score_0_100,
            primary_police_station, primary_junction, recommended_time_window_ist,
            top_violations, top_vehicle_types, representative_location
        ) VALUES %s
        """,
        values,
        page_size=1000,
    )


def load_action_plan(cur):
    rows = read_csv("enforcement_action_plan.csv")
    values = [
        (
            to_int(r["area_rank"]),
            r["priority_band"],
            r["primary_police_station"],
            r["recommended_time_window_IST"],
            to_int(r["suggested_patrol_units"]),
            to_float(r["operational_impact_score_0_100"]),
            to_int(r["records"]),
            to_int(r["zone_count"]),
            r["primary_junction"],
            r["recommended_intervention"],
            r["representative_location"],
        )
        for r in rows
    ]
    execute_values(
        cur,
        """
        INSERT INTO gridlock.enforcement_action_plan (
            area_rank, priority_band, primary_police_station, recommended_time_window_ist,
            suggested_patrol_units, operational_impact_score_0_100, records,
            zone_count, primary_junction, recommended_intervention, representative_location
        ) VALUES %s
        """,
        values,
        page_size=1000,
    )


def load_deployment_plan(cur):
    rows = read_csv("next_day_deployment_plan.csv")
    cur.execute("TRUNCATE gridlock.next_day_deployment_plan;")
    values = [
        (
            r["target_date"],
            to_int(r["area_rank"]),
            r["target_weekday"],
            r["deployment_status"],
            r["priority_band"],
            r["primary_police_station"],
            r["recommended_time_window_IST"],
            to_int(r["suggested_patrol_units"]),
            to_float(r["operational_impact_score_0_100"]),
            to_int(r["historical_area_records"]),
            to_int(r["station_same_weekday_baseline"]),
            to_int(r["station_same_hour_baseline"]),
            r["recommended_intervention"],
            r["primary_junction"],
            r["representative_location"],
            r["field_success_metric"],
        )
        for r in rows
    ]
    execute_values(
        cur,
        """
        INSERT INTO gridlock.next_day_deployment_plan (
            target_date, area_rank, target_weekday, deployment_status, priority_band,
            primary_police_station, recommended_time_window_ist, suggested_patrol_units,
            operational_impact_score_0_100, historical_area_records,
            station_same_weekday_baseline, station_same_hour_baseline,
            recommended_intervention, primary_junction, representative_location,
            field_success_metric
        ) VALUES %s
        """,
        values,
        page_size=1000,
    )


def main():
    with connect() as conn:
        with conn.cursor() as cur:
            load_hotspot_cells(cur)
            load_hotspot_areas(cur)
            load_action_plan(cur)
            load_deployment_plan(cur)
        conn.commit()
    print("Loaded analytics outputs into PostgreSQL.")


if __name__ == "__main__":
    main()
