from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd
from psycopg2.extras import Json
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from db import connect


MODEL_VERSION = "area-hour-automl-v2"
RANDOM_SEED = 42
MIN_CELL_RECORDS = 100
TOP_ZONE_LIMIT = 250
CLUSTER_RADIUS_METERS = 180
IMPORTANCE_SAMPLE_LIMIT = 12000

VIOLATION_SEVERITY = {
    "PARKING IN A MAIN ROAD": 5,
    "DOUBLE PARKING": 5,
    "PARKING NEAR ROAD CROSSING": 5,
    "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS": 5,
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC": 4,
    "PARKING ON FOOTPATH": 3,
    "WRONG PARKING": 2,
    "NO PARKING": 2,
}

VEHICLE_OBSTRUCTION = {
    "BUS (BMTC/KSRTC)": 5,
    "PRIVATE BUS": 5,
    "LGV": 4,
    "VAN": 4,
    "TEMPO": 4,
    "MAXI-CAB": 3,
    "CAR": 3,
    "GOODS AUTO": 3,
    "PASSENGER AUTO": 2.5,
    "SCOOTER": 1,
    "MOTOR CYCLE": 1,
    "MOPED": 1,
}


def parse_violation_labels(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except json.JSONDecodeError:
            return [value]
    return [str(value)]


def haversine_meters(lat1, lon1, lat2, lon2):
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find(parent, item):
    while parent[item] != item:
        parent[item] = parent[parent[item]]
        item = parent[item]
    return item


def union(parent, left, right):
    left_root = find(parent, left)
    right_root = find(parent, right)
    if left_root != right_root:
        parent[right_root] = left_root


def precision_at(y_true, y_score, k):
    if len(y_true) == 0:
        return 0.0
    k = min(k, len(y_true))
    top = np.argsort(-np.asarray(y_score))[:k]
    return float(np.mean(np.asarray(y_true)[top]))


def recall_at(y_true, y_score, k):
    positives = np.asarray(y_true).sum()
    if positives == 0:
        return 0.0
    k = min(k, len(y_true))
    top = np.argsort(-np.asarray(y_score))[:k]
    return float(np.asarray(y_true)[top].sum() / positives)


def to_native(value):
    if isinstance(value, dict):
        return {key: to_native(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_native(item) for item in value]
    if isinstance(value, tuple):
        return [to_native(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def fetch_raw_records():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    latitude::float AS latitude,
                    longitude::float AS longitude,
                    police_station,
                    junction_name,
                    vehicle_type,
                    violation_type::text AS violation_type,
                    created_datetime
                FROM gridlock.parking_violations_raw
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND police_station IS NOT NULL
                  AND created_datetime IS NOT NULL
                """
            )
            rows = cur.fetchall()
            columns = [column.name for column in cur.description]
    return pd.DataFrame(rows, columns=columns)


def build_area_lookup(raw):
    zones = raw.groupby(["lat_cell", "lon_cell"], observed=True).size().reset_index(name="records")
    zones = zones[zones["records"] >= MIN_CELL_RECORDS].sort_values("records", ascending=False).head(TOP_ZONE_LIMIT)
    zones = zones.reset_index(drop=True)
    if zones.empty:
        raise RuntimeError("No eligible hotspot cells found for ML training.")

    parent = {index: index for index in range(len(zones))}
    for i, left in zones.iterrows():
        for j in range(i + 1, len(zones)):
            right = zones.iloc[j]
            distance = haversine_meters(left["lat_cell"], left["lon_cell"], right["lat_cell"], right["lon_cell"])
            if distance <= CLUSTER_RADIUS_METERS:
                union(parent, i, j)

    grouped = defaultdict(list)
    for index, zone in zones.iterrows():
        grouped[find(parent, index)].append(zone)

    area_lookup = {}
    area_meta = []
    for area_index, group in enumerate(grouped.values(), start=1):
        group_df = pd.DataFrame(group)
        total_records = group_df["records"].sum()
        center_lat = float(np.average(group_df["lat_cell"], weights=group_df["records"]))
        center_lon = float(np.average(group_df["lon_cell"], weights=group_df["records"]))
        for _, row in group_df.iterrows():
            area_lookup[(float(row["lat_cell"]), float(row["lon_cell"]))] = area_index
        area_meta.append(
            {
                "area_id": area_index,
                "center_lat": round(center_lat, 6),
                "center_lon": round(center_lon, 6),
                "historical_records": int(total_records),
            }
        )

    return area_lookup, pd.DataFrame(area_meta)


def build_event_frame(raw):
    raw = raw.copy()
    raw["created_datetime"] = pd.to_datetime(raw["created_datetime"], utc=True)
    raw["local_datetime"] = raw["created_datetime"].dt.tz_convert("Asia/Kolkata")
    raw["event_date"] = raw["local_datetime"].dt.floor("D")
    raw["hour"] = raw["local_datetime"].dt.hour
    raw["weekday"] = raw["local_datetime"].dt.weekday
    raw["is_weekend"] = (raw["weekday"] >= 5).astype(int)
    raw["lat_cell"] = raw["latitude"].round(3)
    raw["lon_cell"] = raw["longitude"].round(3)

    area_lookup, area_meta = build_area_lookup(raw)
    raw["area_id"] = [area_lookup.get((lat, lon)) for lat, lon in zip(raw["lat_cell"], raw["lon_cell"])]
    raw = raw.dropna(subset=["area_id"]).copy()
    raw["area_id"] = raw["area_id"].astype(int)

    severity_values = []
    main_road_flags = []
    double_parking_flags = []
    crossing_flags = []
    for value in raw["violation_type"]:
        labels = parse_violation_labels(value)
        severity_values.append(max([VIOLATION_SEVERITY.get(label, 1) for label in labels] or [1]))
        main_road_flags.append(int("PARKING IN A MAIN ROAD" in labels))
        double_parking_flags.append(int("DOUBLE PARKING" in labels))
        crossing_flags.append(
            int(
                any(
                    label in {
                        "PARKING NEAR ROAD CROSSING",
                        "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS",
                    }
                    for label in labels
                )
            )
        )

    raw["severity_value"] = severity_values
    raw["main_road_flag"] = main_road_flags
    raw["double_parking_flag"] = double_parking_flags
    raw["crossing_flag"] = crossing_flags
    raw["junction_flag"] = (~raw["junction_name"].fillna("NULL").isin(["NULL", "No Junction", ""])).astype(int)
    raw["vehicle_obstruction"] = raw["vehicle_type"].map(VEHICLE_OBSTRUCTION).fillna(1.0)

    grouped = (
        raw.groupby(["area_id", "hour", "event_date"], observed=True)
        .agg(
            records=("area_id", "size"),
            severity_total=("severity_value", "sum"),
            severity_mean=("severity_value", "mean"),
            obstruction_mean=("vehicle_obstruction", "mean"),
            junction_share=("junction_flag", "mean"),
            main_road_share=("main_road_flag", "mean"),
            double_parking_share=("double_parking_flag", "mean"),
            crossing_share=("crossing_flag", "mean"),
            active_cells=("lat_cell", "nunique"),
            police_station=("police_station", lambda values: values.mode().iat[0] if not values.mode().empty else values.iloc[0]),
        )
        .reset_index()
    )

    grouped = grouped.merge(area_meta, on="area_id", how="left")

    all_dates = pd.date_range(grouped["event_date"].min(), grouped["event_date"].max(), freq="D")
    frames = []
    for (area_id, hour), bucket in grouped.groupby(["area_id", "hour"], sort=False):
        bucket = bucket.set_index("event_date").reindex(all_dates).rename_axis("event_date").reset_index()
        bucket["area_id"] = area_id
        bucket["hour"] = hour
        bucket["records"] = bucket["records"].fillna(0)
        bucket["severity_total"] = bucket["severity_total"].fillna(0)
        bucket["severity_mean"] = bucket["severity_mean"].fillna(0)
        bucket["obstruction_mean"] = bucket["obstruction_mean"].fillna(0)
        bucket["junction_share"] = bucket["junction_share"].fillna(0)
        bucket["main_road_share"] = bucket["main_road_share"].fillna(0)
        bucket["double_parking_share"] = bucket["double_parking_share"].fillna(0)
        bucket["crossing_share"] = bucket["crossing_share"].fillna(0)
        bucket["active_cells"] = bucket["active_cells"].fillna(0)
        bucket["police_station"] = bucket["police_station"].ffill().bfill()
        bucket["center_lat"] = bucket["center_lat"].ffill().bfill()
        bucket["center_lon"] = bucket["center_lon"].ffill().bfill()
        bucket["historical_records"] = bucket["historical_records"].ffill().bfill()
        frames.append(bucket)

    samples = pd.concat(frames, ignore_index=True)
    samples = samples.sort_values(["area_id", "hour", "event_date"])
    samples["weekday"] = samples["event_date"].dt.weekday
    samples["is_weekend"] = (samples["weekday"] >= 5).astype(int)
    return samples


def add_features(samples):
    samples = samples.copy()
    by_bucket = samples.groupby(["area_id", "hour"], sort=False)

    samples["lag_1_records"] = by_bucket["records"].shift(1).fillna(0)
    samples["lag_3_records"] = by_bucket["records"].shift(3).fillna(0)
    samples["lag_7_records"] = by_bucket["records"].shift(7).fillna(0)
    samples["lag_14_records"] = by_bucket["records"].shift(14).fillna(0)
    samples["rolling_3_records"] = by_bucket["records"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean()).fillna(0)
    samples["rolling_7_records"] = by_bucket["records"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean()).fillna(0)
    samples["rolling_14_records"] = by_bucket["records"].transform(lambda s: s.shift(1).rolling(14, min_periods=1).mean()).fillna(0)
    samples["rolling_21_records"] = by_bucket["records"].transform(lambda s: s.shift(1).rolling(21, min_periods=1).mean()).fillna(0)
    samples["active_days_14"] = by_bucket["records"].transform(lambda s: (s.shift(1).fillna(0) > 0).rolling(14, min_periods=1).sum()).fillna(0)
    samples["active_days_21"] = by_bucket["records"].transform(lambda s: (s.shift(1).fillna(0) > 0).rolling(21, min_periods=1).sum()).fillna(0)
    samples["rolling_severity_7"] = by_bucket["severity_total"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean()).fillna(0)
    samples["rolling_severity_14"] = by_bucket["severity_total"].transform(lambda s: s.shift(1).rolling(14, min_periods=1).mean()).fillna(0)
    samples["rolling_obstruction_7"] = by_bucket["obstruction_mean"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean()).fillna(0)
    samples["rolling_junction_share_7"] = by_bucket["junction_share"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean()).fillna(0)
    samples["rolling_main_road_share_7"] = by_bucket["main_road_share"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean()).fillna(0)
    samples["rolling_double_parking_share_7"] = by_bucket["double_parking_share"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean()).fillna(0)
    samples["rolling_crossing_share_7"] = by_bucket["crossing_share"].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean()).fillna(0)
    samples["trend_3_vs_14"] = samples["rolling_3_records"] - samples["rolling_14_records"]
    samples["trend_7_vs_21"] = samples["rolling_7_records"] - samples["rolling_21_records"]
    samples["severity_per_record"] = np.where(samples["records"] > 0, samples["severity_total"] / samples["records"], 0)

    station_hour_mean = samples.groupby(["police_station", "hour"])["records"].transform("mean")
    station_mean = samples.groupby("police_station")["records"].transform("mean")
    area_hour_mean = samples.groupby(["area_id", "hour"])["records"].transform("mean")
    samples["station_hour_mean"] = station_hour_mean.fillna(station_mean).fillna(samples["records"].mean())
    samples["area_hour_mean"] = area_hour_mean.fillna(samples["records"].mean())
    samples["hour_sin"] = np.sin(2 * np.pi * samples["hour"] / 24)
    samples["hour_cos"] = np.cos(2 * np.pi * samples["hour"] / 24)
    samples["weekday_sin"] = np.sin(2 * np.pi * samples["weekday"] / 7)
    samples["weekday_cos"] = np.cos(2 * np.pi * samples["weekday"] / 7)

    samples["impact_proxy"] = (
        samples["records"]
        + 0.35 * samples["severity_total"]
        + 0.20 * samples["rolling_obstruction_7"]
        + 2.0 * samples["junction_share"]
        + 3.0 * samples["main_road_share"]
        + 2.5 * samples["double_parking_share"]
        + 1.5 * samples["crossing_share"]
    )
    samples["next_day_records"] = by_bucket["records"].shift(-1).fillna(0)
    samples["next_day_impact_proxy"] = by_bucket["impact_proxy"].shift(-1).fillna(0)
    return samples


def prepare_model_frame(samples):
    usable = samples[samples["event_date"] < samples["event_date"].max()].copy()
    positive_impact = usable.loc[usable["next_day_impact_proxy"] > 0, "next_day_impact_proxy"]
    positive_records = usable.loc[usable["next_day_records"] > 0, "next_day_records"]

    impact_threshold = max(4.0, float(positive_impact.quantile(0.78))) if len(positive_impact) else 4.0
    records_threshold = max(2.0, float(positive_records.quantile(0.72))) if len(positive_records) else 2.0

    usable["target_high_risk"] = (
        (usable["next_day_impact_proxy"] >= impact_threshold)
        | (usable["next_day_records"] >= records_threshold)
    ).astype(int)
    return usable, impact_threshold, records_threshold


def build_sample_weight(y_train):
    positives = max(float(np.sum(y_train)), 1.0)
    negatives = max(float(len(y_train) - np.sum(y_train)), 1.0)
    positive_weight = negatives / positives
    return np.where(y_train == 1, positive_weight, 1.0)


def build_candidate_models():
    return [
        {
            "name": "hgb_ranker_v1",
            "algorithm": "scikit-learn HistGradientBoostingClassifier",
            "builder": lambda: HistGradientBoostingClassifier(
                loss="log_loss",
                learning_rate=0.05,
                max_iter=250,
                max_leaf_nodes=31,
                min_samples_leaf=20,
                l2_regularization=0.05,
                max_depth=6,
                early_stopping=True,
                random_state=RANDOM_SEED,
            ),
        },
        {
            "name": "hgb_ranker_v2",
            "algorithm": "scikit-learn HistGradientBoostingClassifier",
            "builder": lambda: HistGradientBoostingClassifier(
                loss="log_loss",
                learning_rate=0.04,
                max_iter=340,
                max_leaf_nodes=63,
                min_samples_leaf=12,
                l2_regularization=0.03,
                max_depth=8,
                early_stopping=True,
                random_state=RANDOM_SEED,
            ),
        },
        {
            "name": "rf_ranker_v1",
            "algorithm": "scikit-learn RandomForestClassifier",
            "builder": lambda: RandomForestClassifier(
                n_estimators=360,
                max_depth=18,
                min_samples_leaf=3,
                class_weight="balanced_subsample",
                random_state=RANDOM_SEED,
                n_jobs=1,
            ),
        },
    ]


def calculate_metrics(y_true, y_score):
    return to_native(
        {
            "precision_at_10": precision_at(y_true, y_score, 10),
            "precision_at_20": precision_at(y_true, y_score, 20),
            "precision_at_50": precision_at(y_true, y_score, 50),
            "precision_at_80": precision_at(y_true, y_score, 80),
            "recall_at_50": recall_at(y_true, y_score, 50),
            "recall_at_80": recall_at(y_true, y_score, 80),
            "roc_auc": roc_auc_score(y_true, y_score),
            "average_precision": average_precision_score(y_true, y_score),
            "brier_score": brier_score_loss(y_true, y_score),
            "log_loss": log_loss(y_true, y_score, labels=[0, 1]),
        }
    )


def metrics_rank_key(metrics):
    return (
        metrics["precision_at_20"],
        metrics["precision_at_50"],
        metrics["roc_auc"],
        metrics["average_precision"],
        metrics["recall_at_50"],
        -metrics["log_loss"],
        -metrics["brier_score"],
    )


def train_best_model(x_train, y_train, x_holdout, y_holdout):
    sample_weight = build_sample_weight(y_train)
    benchmark_results = []
    best = None

    for candidate in build_candidate_models():
        model = candidate["builder"]()
        model.fit(x_train, y_train, sample_weight=sample_weight)
        holdout_prob = model.predict_proba(x_holdout)[:, 1]
        metrics = calculate_metrics(y_holdout, holdout_prob)
        benchmark_results.append(
            {
                "name": candidate["name"],
                "algorithm": candidate["algorithm"],
                "metrics": metrics,
                "params": to_native(model.get_params()),
            }
        )
        candidate_result = {
            "name": candidate["name"],
            "algorithm": candidate["algorithm"],
            "model": model,
            "metrics": metrics,
            "holdout_prob": holdout_prob,
        }
        if best is None or metrics_rank_key(metrics) > metrics_rank_key(best["metrics"]):
            best = candidate_result

    benchmark_results = sorted(benchmark_results, key=lambda row: metrics_rank_key(row["metrics"]), reverse=True)
    for index, row in enumerate(benchmark_results, start=1):
        row["rank"] = index
        row["selected"] = row["name"] == best["name"]
    return best, benchmark_results


def compute_feature_importance(model, x_holdout, y_holdout, feature_names):
    if len(x_holdout) > IMPORTANCE_SAMPLE_LIMIT:
        rng = np.random.default_rng(RANDOM_SEED)
        indices = rng.choice(len(x_holdout), size=IMPORTANCE_SAMPLE_LIMIT, replace=False)
        sample_x = x_holdout[indices]
        sample_y = y_holdout[indices]
    else:
        sample_x = x_holdout
        sample_y = y_holdout

    importance = permutation_importance(
        model,
        sample_x,
        sample_y,
        scoring="average_precision",
        n_repeats=5,
        random_state=RANDOM_SEED,
        n_jobs=1,
    )
    rows = []
    for name, mean, std in zip(feature_names, importance.importances_mean, importance.importances_std):
        rows.append(
            {
                "feature": name,
                "importance_mean": float(mean),
                "importance_std": float(std),
            }
        )
    rows.sort(key=lambda row: row["importance_mean"], reverse=True)
    return rows


def build_reference_profile(train_df):
    explain_features = [
        "records",
        "lag_1_records",
        "lag_7_records",
        "rolling_3_records",
        "rolling_7_records",
        "rolling_14_records",
        "active_days_14",
        "rolling_severity_7",
        "rolling_obstruction_7",
        "rolling_junction_share_7",
        "rolling_main_road_share_7",
        "rolling_double_parking_share_7",
        "rolling_crossing_share_7",
        "trend_3_vs_14",
        "station_hour_mean",
        "area_hour_mean",
    ]
    return {feature: float(train_df[feature].median()) for feature in explain_features}


def build_risk_explanation(row, baselines, importance_map):
    drivers = []

    def add_count_driver(feature, label, narrative, floor):
        value = float(row[feature])
        baseline = float(baselines.get(feature, 0.0))
        if value < max(floor, baseline * 1.15):
            return
        lift = (value - baseline) / (abs(baseline) + 1.0)
        score = lift * (0.05 + importance_map.get(feature, 0.02))
        drivers.append(
            {
                "feature": feature,
                "label": label,
                "score": float(score),
                "detail": narrative.format(value=round(value, 2), baseline=round(baseline, 2)),
            }
        )

    def add_share_driver(feature, label, narrative, min_delta):
        value = float(row[feature])
        baseline = float(baselines.get(feature, 0.0))
        delta = value - baseline
        if delta < min_delta:
            return
        score = delta * 8.0 * (0.05 + importance_map.get(feature, 0.02))
        drivers.append(
            {
                "feature": feature,
                "label": label,
                "score": float(score),
                "detail": narrative.format(value=round(value * 100, 1), baseline=round(baseline * 100, 1)),
            }
        )

    add_count_driver(
        "rolling_7_records",
        "Sustained repeat parking pressure",
        "Seven-day hourly average is {value} versus a baseline of {baseline}.",
        3.0,
    )
    add_count_driver(
        "trend_3_vs_14",
        "Recent surge over the normal pattern",
        "Short-term trend is {value} above the 14-day pattern, versus a baseline of {baseline}.",
        1.0,
    )
    add_count_driver(
        "active_days_14",
        "Persistent hotspot across many days",
        "This area-hour was active on {value} of the last 14 days, versus a baseline of {baseline}.",
        6.0,
    )
    add_count_driver(
        "lag_1_records",
        "Activity also appeared yesterday",
        "Yesterday this same area-hour logged {value} records, versus a baseline of {baseline}.",
        2.0,
    )
    add_count_driver(
        "lag_7_records",
        "Weekly recurrence is visible",
        "A week ago this same area-hour logged {value} records, versus a baseline of {baseline}.",
        2.0,
    )
    add_share_driver(
        "rolling_main_road_share_7",
        "Main-road blocking pattern",
        "Main-road parking forms {value}% of recent cases here, versus {baseline}% normally.",
        0.10,
    )
    add_share_driver(
        "rolling_double_parking_share_7",
        "Double-parking risk is elevated",
        "Double parking forms {value}% of recent cases here, versus {baseline}% normally.",
        0.08,
    )
    add_share_driver(
        "rolling_junction_share_7",
        "Junction-linked pressure is elevated",
        "Junction-linked cases form {value}% of recent cases here, versus {baseline}% normally.",
        0.10,
    )
    add_share_driver(
        "rolling_crossing_share_7",
        "Crossing-side conflict is elevated",
        "Crossing-related cases form {value}% of recent cases here, versus {baseline}% normally.",
        0.06,
    )
    add_count_driver(
        "rolling_obstruction_7",
        "Vehicle obstruction mix is heavier",
        "The obstruction score is {value} versus a baseline of {baseline}.",
        1.8,
    )
    add_count_driver(
        "rolling_severity_7",
        "Violation severity remains elevated",
        "Recent severity totals are {value} versus a baseline of {baseline}.",
        6.0,
    )

    if not drivers:
        drivers.append(
            {
                "feature": "station_hour_mean",
                "label": "Historical station-hour recurrence",
                "score": float(0.01 + importance_map.get("station_hour_mean", 0.02)),
                "detail": (
                    f"Even without a sharp spike, this station-hour historically averages "
                    f"{row['station_hour_mean']:.2f} records."
                ),
            }
        )

    drivers = sorted(drivers, key=lambda item: item["score"], reverse=True)[:3]
    summary = "High risk because " + "; ".join(driver["label"].lower() for driver in drivers) + "."
    return {
        "summary": summary,
        "drivers": [
            {
                "feature": driver["feature"],
                "label": driver["label"],
                "detail": driver["detail"],
            }
            for driver in drivers
        ],
    }


def risk_band(probability):
    if probability >= 0.76:
        return "Critical ML risk"
    if probability >= 0.56:
        return "High ML risk"
    if probability >= 0.36:
        return "Medium ML risk"
    return "Watch"


def build_prediction_payload(row, feature_names, baselines, importance_rows):
    importance_map = {item["feature"]: max(item["importance_mean"], 0.0) for item in importance_rows}
    explanation = build_risk_explanation(row, baselines, importance_map)
    return {
        "model_inputs": {name: float(row[name]) for name in feature_names},
        "risk_summary": explanation["summary"],
        "risk_drivers": explanation["drivers"],
        "operational_flags": {
            "persistent_hotspot": bool(float(row["active_days_14"]) >= 8),
            "recent_surge": bool(float(row["trend_3_vs_14"]) >= 2.0),
            "main_road_pattern": bool(float(row["rolling_main_road_share_7"]) >= 0.20),
            "double_parking_pattern": bool(float(row["rolling_double_parking_share_7"]) >= 0.15),
        },
    }


def main():
    raw = fetch_raw_records()
    if raw.empty:
        raise RuntimeError("No raw parking violation records available for ML training.")

    event_frame = build_event_frame(raw)
    samples = add_features(event_frame)
    model_frame, impact_threshold, records_threshold = prepare_model_frame(samples)

    max_date = model_frame["event_date"].max()
    holdout_start = max_date - pd.Timedelta(days=30)
    train_df = model_frame[model_frame["event_date"] < holdout_start].copy()
    holdout_df = model_frame[model_frame["event_date"] >= holdout_start].copy()

    feature_names = [
        "records",
        "lag_1_records",
        "lag_3_records",
        "lag_7_records",
        "lag_14_records",
        "rolling_3_records",
        "rolling_7_records",
        "rolling_14_records",
        "rolling_21_records",
        "active_days_14",
        "active_days_21",
        "rolling_severity_7",
        "rolling_severity_14",
        "rolling_obstruction_7",
        "rolling_junction_share_7",
        "rolling_main_road_share_7",
        "rolling_double_parking_share_7",
        "rolling_crossing_share_7",
        "trend_3_vs_14",
        "trend_7_vs_21",
        "severity_per_record",
        "station_hour_mean",
        "area_hour_mean",
        "active_cells",
        "historical_records",
        "is_weekend",
        "hour_sin",
        "hour_cos",
        "weekday_sin",
        "weekday_cos",
        "center_lat",
        "center_lon",
    ]

    x_train = train_df[feature_names].astype(float).to_numpy()
    y_train = train_df["target_high_risk"].astype(int).to_numpy()
    x_holdout = holdout_df[feature_names].astype(float).to_numpy()
    y_holdout = holdout_df["target_high_risk"].astype(int).to_numpy()

    best_model, benchmark_results = train_best_model(x_train, y_train, x_holdout, y_holdout)
    model = best_model["model"]
    metrics = best_model["metrics"]
    holdout_prob = best_model["holdout_prob"]
    importance_rows = compute_feature_importance(model, x_holdout, y_holdout, feature_names)
    reference_profile = build_reference_profile(train_df)

    latest_date = samples["event_date"].max()
    target_date = latest_date.date() + timedelta(days=1)
    latest = samples[samples["event_date"] == latest_date].copy()
    latest["ml_risk_probability"] = model.predict_proba(latest[feature_names].astype(float).to_numpy())[:, 1]
    latest["predicted_next_day_records"] = np.maximum(
        0,
        0.45 * latest["rolling_14_records"]
        + 0.35 * latest["rolling_7_records"]
        + 0.20 * latest["rolling_3_records"]
        + 2.4 * latest["ml_risk_probability"],
    )
    latest = latest.sort_values(["ml_risk_probability", "predicted_next_day_records"], ascending=False).head(80)

    model_params = to_native(
        {
            "feature_names": feature_names,
            "impact_threshold_next_day": impact_threshold,
            "records_threshold_next_day": records_threshold,
            "holdout_start": holdout_start.date().isoformat(),
            "latest_training_date": latest_date.date().isoformat(),
            "area_count": int(samples["area_id"].nunique()),
            "selected_candidate": best_model["name"],
            "model_class": best_model["algorithm"],
            "model_settings": model.get_params(),
            "feature_importance": importance_rows[:10],
            "benchmark_results": benchmark_results,
            "extra_metrics": {
                "precision_at_80": metrics["precision_at_80"],
                "recall_at_80": metrics["recall_at_80"],
                "average_precision": metrics["average_precision"],
                "brier_score": metrics["brier_score"],
            },
        }
    )

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM gridlock.ml_hotspot_predictions WHERE model_version = %s", [MODEL_VERSION])
            cur.execute("DELETE FROM gridlock.ml_model_metrics WHERE model_version = %s", [MODEL_VERSION])

            cur.execute(
                """
                INSERT INTO gridlock.ml_model_metrics (
                    model_version, algorithm, training_rows, holdout_rows, positive_rate,
                    precision_at_10, precision_at_20, precision_at_50, recall_at_50,
                    roc_auc, log_loss, feature_names, model_params, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    MODEL_VERSION,
                    best_model["algorithm"],
                    int(len(train_df)),
                    int(len(holdout_df)),
                    float(y_train.mean()),
                    metrics["precision_at_10"],
                    metrics["precision_at_20"],
                    metrics["precision_at_50"],
                    metrics["recall_at_50"],
                    metrics["roc_auc"],
                    metrics["log_loss"],
                    Json(feature_names),
                    Json(model_params),
                    (
                        "Auto-selected the best next-day hotspot ranking model from multiple tabular candidates. "
                        "Uses recurrence, severity, obstruction, and road-context features from parking violations."
                    ),
                ],
            )

            for _, row in latest.iterrows():
                cur.execute(
                    """
                    INSERT INTO gridlock.ml_hotspot_predictions (
                        model_version, target_date, lat_cell, lon_cell, police_station,
                        recommended_time_window_ist, ml_risk_probability,
                        predicted_next_day_records, ml_risk_band, features
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        MODEL_VERSION,
                        target_date,
                        float(row["center_lat"]),
                        float(row["center_lon"]),
                        row["police_station"],
                        f"{int(row['hour']):02d}:00-{int(row['hour']):02d}:59",
                        float(row["ml_risk_probability"]),
                        float(row["predicted_next_day_records"]),
                        risk_band(float(row["ml_risk_probability"])),
                        Json(build_prediction_payload(row, feature_names, reference_profile, importance_rows)),
                    ],
                )
        conn.commit()

    print(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "selected_candidate": best_model["name"],
                "training_rows": int(len(train_df)),
                "holdout_rows": int(len(holdout_df)),
                "target_date": target_date.isoformat(),
                "metrics": metrics,
                "top_feature_importance": importance_rows[:5],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
