CREATE TABLE IF NOT EXISTS gridlock.ml_hotspot_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    model_version TEXT NOT NULL,
    target_date DATE NOT NULL,
    lat_cell NUMERIC(10, 3) NOT NULL,
    lon_cell NUMERIC(10, 3) NOT NULL,
    police_station TEXT,
    recommended_time_window_ist TEXT,
    ml_risk_probability NUMERIC(8, 6) NOT NULL,
    predicted_next_day_records NUMERIC(10, 2) NOT NULL,
    ml_risk_band TEXT NOT NULL,
    features JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_predictions_target_date
    ON gridlock.ml_hotspot_predictions (target_date);

CREATE INDEX IF NOT EXISTS idx_ml_predictions_probability
    ON gridlock.ml_hotspot_predictions (ml_risk_probability DESC);

CREATE TABLE IF NOT EXISTS gridlock.ml_model_metrics (
    model_version TEXT PRIMARY KEY,
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    algorithm TEXT NOT NULL,
    training_rows INTEGER NOT NULL,
    holdout_rows INTEGER NOT NULL,
    positive_rate NUMERIC(8, 6) NOT NULL,
    precision_at_10 NUMERIC(8, 6) NOT NULL,
    precision_at_20 NUMERIC(8, 6) NOT NULL,
    precision_at_50 NUMERIC(8, 6) NOT NULL,
    recall_at_50 NUMERIC(8, 6) NOT NULL,
    roc_auc NUMERIC(8, 6) NOT NULL,
    log_loss NUMERIC(10, 6) NOT NULL,
    feature_names JSONB NOT NULL,
    model_params JSONB NOT NULL,
    notes TEXT
);
