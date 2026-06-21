CREATE OR REPLACE VIEW gridlock.v_parking_violations_enriched AS
SELECT
    id,
    latitude,
    longitude,
    ROUND(latitude::numeric, 3) AS lat_cell,
    ROUND(longitude::numeric, 3) AS lon_cell,
    location,
    vehicle_type,
    violation_type,
    created_datetime,
    created_datetime AT TIME ZONE 'Asia/Kolkata' AS created_datetime_ist,
    EXTRACT(HOUR FROM created_datetime AT TIME ZONE 'Asia/Kolkata')::int AS hour_ist,
    TO_CHAR(created_datetime AT TIME ZONE 'Asia/Kolkata', 'Day') AS weekday_ist,
    police_station,
    junction_name,
    validation_status,
    data_sent_to_scita
FROM gridlock.parking_violations_raw;

CREATE OR REPLACE VIEW gridlock.v_station_daily_load AS
SELECT
    police_station,
    DATE(created_datetime AT TIME ZONE 'Asia/Kolkata') AS violation_date_ist,
    COUNT(*) AS records
FROM gridlock.parking_violations_raw
GROUP BY 1, 2;

CREATE OR REPLACE VIEW gridlock.v_hourly_city_load AS
SELECT
    EXTRACT(HOUR FROM created_datetime AT TIME ZONE 'Asia/Kolkata')::int AS hour_ist,
    COUNT(*) AS records
FROM gridlock.parking_violations_raw
GROUP BY 1;
