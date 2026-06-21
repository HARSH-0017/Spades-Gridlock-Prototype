CREATE SCHEMA IF NOT EXISTS gridlock;

CREATE TABLE IF NOT EXISTS gridlock.parking_violations_raw (
    id TEXT PRIMARY KEY,
    latitude NUMERIC(10, 7) NOT NULL,
    longitude NUMERIC(10, 7) NOT NULL,
    location TEXT,
    vehicle_number TEXT,
    vehicle_type TEXT,
    description TEXT,
    violation_type JSONB,
    offence_code JSONB,
    created_datetime TIMESTAMPTZ NOT NULL,
    closed_datetime TIMESTAMPTZ,
    modified_datetime TIMESTAMPTZ,
    device_id TEXT,
    created_by_id TEXT,
    center_code TEXT,
    police_station TEXT,
    data_sent_to_scita BOOLEAN,
    junction_name TEXT,
    action_taken_timestamp TIMESTAMPTZ,
    data_sent_to_scita_timestamp TIMESTAMPTZ,
    updated_vehicle_number TEXT,
    updated_vehicle_type TEXT,
    validation_status TEXT,
    validation_timestamp TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parking_raw_station
    ON gridlock.parking_violations_raw (police_station);

CREATE INDEX IF NOT EXISTS idx_parking_raw_created
    ON gridlock.parking_violations_raw (created_datetime);

CREATE INDEX IF NOT EXISTS idx_parking_raw_location
    ON gridlock.parking_violations_raw (latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_parking_raw_junction
    ON gridlock.parking_violations_raw (junction_name);

CREATE TABLE IF NOT EXISTS gridlock.hotspot_cells (
    lat_cell NUMERIC(10, 3) NOT NULL,
    lon_cell NUMERIC(10, 3) NOT NULL,
    records INTEGER NOT NULL,
    active_days INTEGER NOT NULL,
    priority_score_0_100 NUMERIC(6, 2) NOT NULL,
    police_station TEXT,
    junction TEXT,
    peak_hour_ist TEXT,
    peak_hour_count INTEGER,
    peak_hour_share NUMERIC(8, 4),
    top_weekday TEXT,
    avg_violation_severity_1_5 NUMERIC(5, 2),
    avg_vehicle_obstruction_1_5 NUMERIC(5, 2),
    top_violations TEXT,
    top_vehicle_types TEXT,
    sample_location TEXT,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (lat_cell, lon_cell)
);

CREATE TABLE IF NOT EXISTS gridlock.hotspot_areas (
    area_rank INTEGER PRIMARY KEY,
    center_lat NUMERIC(10, 6) NOT NULL,
    center_lon NUMERIC(10, 6) NOT NULL,
    zone_count INTEGER NOT NULL,
    records INTEGER NOT NULL,
    max_active_days INTEGER NOT NULL,
    area_priority_score_0_100 NUMERIC(6, 2) NOT NULL,
    operational_impact_score_0_100 NUMERIC(6, 2) NOT NULL,
    primary_police_station TEXT,
    primary_junction TEXT,
    recommended_time_window_ist TEXT,
    top_violations TEXT,
    top_vehicle_types TEXT,
    representative_location TEXT,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gridlock.enforcement_action_plan (
    area_rank INTEGER PRIMARY KEY REFERENCES gridlock.hotspot_areas(area_rank) ON DELETE CASCADE,
    priority_band TEXT NOT NULL,
    primary_police_station TEXT,
    recommended_time_window_ist TEXT,
    suggested_patrol_units INTEGER NOT NULL,
    operational_impact_score_0_100 NUMERIC(6, 2) NOT NULL,
    records INTEGER NOT NULL,
    zone_count INTEGER NOT NULL,
    primary_junction TEXT,
    recommended_intervention TEXT,
    representative_location TEXT,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gridlock.next_day_deployment_plan (
    target_date DATE NOT NULL,
    area_rank INTEGER NOT NULL,
    target_weekday TEXT,
    deployment_status TEXT,
    priority_band TEXT,
    primary_police_station TEXT,
    recommended_time_window_ist TEXT,
    suggested_patrol_units INTEGER,
    operational_impact_score_0_100 NUMERIC(6, 2),
    historical_area_records INTEGER,
    station_same_weekday_baseline INTEGER,
    station_same_hour_baseline INTEGER,
    recommended_intervention TEXT,
    primary_junction TEXT,
    representative_location TEXT,
    field_success_metric TEXT,
    built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (target_date, area_rank)
);

CREATE TABLE IF NOT EXISTS gridlock.field_interventions (
    intervention_id BIGSERIAL PRIMARY KEY,
    intervention_date DATE NOT NULL,
    area_rank INTEGER REFERENCES gridlock.hotspot_areas(area_rank),
    police_station TEXT NOT NULL,
    time_window_ist TEXT NOT NULL,
    deployed_units INTEGER,
    intervention_done BOOLEAN,
    vehicles_warned INTEGER,
    vehicles_towed INTEGER,
    violations_recorded_during_patrol INTEGER,
    repeat_violation_check_after_7_days INTEGER,
    field_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
