import csv
import json
from datetime import datetime

from psycopg2.extras import execute_values

from config import SOURCE_CSV
from db import connect


BATCH_SIZE = 5000

INSERT_SQL = """
INSERT INTO gridlock.parking_violations_raw (
    id, latitude, longitude, location, vehicle_number, vehicle_type, description,
    violation_type, offence_code, created_datetime, closed_datetime, modified_datetime,
    device_id, created_by_id, center_code, police_station, data_sent_to_scita,
    junction_name, action_taken_timestamp, data_sent_to_scita_timestamp,
    updated_vehicle_number, updated_vehicle_type, validation_status, validation_timestamp
) VALUES %s
ON CONFLICT (id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    location = EXCLUDED.location,
    vehicle_number = EXCLUDED.vehicle_number,
    vehicle_type = EXCLUDED.vehicle_type,
    description = EXCLUDED.description,
    violation_type = EXCLUDED.violation_type,
    offence_code = EXCLUDED.offence_code,
    created_datetime = EXCLUDED.created_datetime,
    modified_datetime = EXCLUDED.modified_datetime,
    police_station = EXCLUDED.police_station,
    junction_name = EXCLUDED.junction_name,
    validation_status = EXCLUDED.validation_status,
    validation_timestamp = EXCLUDED.validation_timestamp,
    ingested_at = NOW();
"""


def null_if_empty(value):
    value = (value or "").strip()
    return None if not value or value.upper() == "NULL" else value


def parse_bool(value):
    value = null_if_empty(value)
    if value is None:
        return None
    return value.upper() == "TRUE"


def parse_json(value):
    value = null_if_empty(value)
    if value is None:
        return None
    try:
        return json.dumps(json.loads(value))
    except json.JSONDecodeError:
        return json.dumps([value])


def parse_ts(value):
    value = null_if_empty(value)
    if value is None:
        return None
    return value


def row_to_tuple(row):
    return (
        row["id"],
        float(row["latitude"]),
        float(row["longitude"]),
        null_if_empty(row.get("location")),
        null_if_empty(row.get("vehicle_number")),
        null_if_empty(row.get("vehicle_type")),
        null_if_empty(row.get("description")),
        parse_json(row.get("violation_type")),
        parse_json(row.get("offence_code")),
        parse_ts(row.get("created_datetime")),
        parse_ts(row.get("closed_datetime")),
        parse_ts(row.get("modified_datetime")),
        null_if_empty(row.get("device_id")),
        null_if_empty(row.get("created_by_id")),
        null_if_empty(row.get("center_code")),
        null_if_empty(row.get("police_station")),
        parse_bool(row.get("data_sent_to_scita")),
        null_if_empty(row.get("junction_name")),
        parse_ts(row.get("action_taken_timestamp")),
        parse_ts(row.get("data_sent_to_scita_timestamp")),
        null_if_empty(row.get("updated_vehicle_number")),
        null_if_empty(row.get("updated_vehicle_type")),
        null_if_empty(row.get("validation_status")),
        parse_ts(row.get("validation_timestamp")),
    )


def flush(cur, batch):
    execute_values(cur, INSERT_SQL, batch, page_size=len(batch))


def main():
    started = datetime.now()
    inserted = 0
    batch = []

    with connect() as conn:
        with conn.cursor() as cur:
            with SOURCE_CSV.open(newline="", encoding="utf-8-sig", errors="replace") as csv_file:
                for row in csv.DictReader(csv_file):
                    batch.append(row_to_tuple(row))
                    if len(batch) >= BATCH_SIZE:
                        flush(cur, batch)
                        inserted += len(batch)
                        print(f"Upserted {inserted:,} rows")
                        batch.clear()
                if batch:
                    flush(cur, batch)
                    inserted += len(batch)
            conn.commit()

    elapsed = datetime.now() - started
    print(f"Finished upserting {inserted:,} rows in {elapsed}.")


if __name__ == "__main__":
    main()
