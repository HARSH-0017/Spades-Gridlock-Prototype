-- Paste these into pgAdmin Query Tool after running the ingestion/setup pipeline.

-- 1. Confirm raw ingestion count.
SELECT COUNT(*) AS raw_violation_records
FROM gridlock.parking_violations_raw;

-- 2. Top police stations by violation volume.
SELECT police_station, COUNT(*) AS records
FROM gridlock.parking_violations_raw
GROUP BY police_station
ORDER BY records DESC
LIMIT 20;

-- 3. Top operational hotspot areas.
SELECT
    area_rank,
    primary_police_station,
    primary_junction,
    records,
    operational_impact_score_0_100,
    recommended_time_window_ist,
    representative_location
FROM gridlock.hotspot_areas
ORDER BY operational_impact_score_0_100 DESC, records DESC
LIMIT 25;

-- 4. Next-day deployment plan.
SELECT
    target_date,
    deployment_status,
    priority_band,
    primary_police_station,
    recommended_time_window_ist,
    suggested_patrol_units,
    operational_impact_score_0_100,
    recommended_intervention
FROM gridlock.next_day_deployment_plan
ORDER BY
    CASE deployment_status
        WHEN 'Deploy' THEN 1
        WHEN 'Targeted patrol' THEN 2
        ELSE 3
    END,
    operational_impact_score_0_100 DESC;

-- 5. Field intervention effectiveness once teams begin filling the tracker.
SELECT
    police_station,
    COUNT(*) AS interventions,
    SUM(vehicles_warned) AS vehicles_warned,
    SUM(vehicles_towed) AS vehicles_towed,
    AVG(repeat_violation_check_after_7_days) AS avg_repeat_violations_after_7_days
FROM gridlock.field_interventions
GROUP BY police_station
ORDER BY interventions DESC;
