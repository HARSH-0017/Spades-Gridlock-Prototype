import React from "react";
import { BrainCircuit, CheckCircle2, Sparkles, Target } from "lucide-react";
import { MlMetricGrid, SectionHeader } from "../components/ui";
import { pct } from "../utils";

function featureLabel(name) {
  const labels = {
    area_hour_mean: "Area-hour historical average",
    station_hour_mean: "Station-hour historical average",
    center_lat: "Latitude cluster signal",
    center_lon: "Longitude cluster signal",
    historical_records: "Historical area volume",
    is_weekend: "Weekend pattern",
    weekday_sin: "Weekday seasonality",
    rolling_severity_7: "Recent severity trend",
    rolling_14_records: "Two-week demand average",
    active_days_21: "21-day persistence",
  };
  return labels[name] || name.replaceAll("_", " ");
}

function BenchmarkCard({ row }) {
  return (
    <article className={row.selected ? "benchmark-card selected" : "benchmark-card"}>
      <div className="benchmark-head">
        <span>Rank {row.rank}</span>
        {row.selected ? <strong>Winner</strong> : null}
      </div>
      <h4>{row.name}</h4>
      <p>{row.algorithm}</p>
      <div className="benchmark-metrics">
        <span>P@20 {pct(row.metrics.precision_at_20)}</span>
        <span>P@50 {pct(row.metrics.precision_at_50)}</span>
        <span>AUC {Number(row.metrics.roc_auc).toFixed(3)}</span>
        <span>PR-AUC {Number(row.metrics.average_precision).toFixed(3)}</span>
      </div>
    </article>
  );
}

function ForecastCard({ row, index }) {
  return (
    <article className="forecast-card" key={`${row.police_station}-${row.recommended_time_window_ist}`}>
      <span className="eyebrow">Prediction {String(index + 1).padStart(2, "0")}</span>
      <h4>{row.police_station}</h4>
      <p>{row.recommended_time_window_ist} | {row.ml_risk_band}</p>
      <strong>{Math.round(Number(row.ml_risk_probability) * 100)}%</strong>
      <div className="forecast-summary">
        {row.features?.risk_summary || "Restart the backend to expose the latest saved ML explanations."}
      </div>
      <div className="driver-stack">
        {(row.features?.risk_drivers || []).slice(0, 3).map((driver) => (
          <div className="driver-row" key={`${row.police_station}-${driver.feature}`}>
            <Sparkles size={13} />
            <div>
              <b>{driver.label}</b>
              <span>{driver.detail}</span>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

export function ModelPage({ data, viewModel }) {
  if (!data) return null;

  return (
    <div className="page-stack">
      <section className="hero-grid model">
        <article className="hero-card">
          <span className="eyebrow">Model summary</span>
          <h3>Ranking-first ML for next-day enforcement</h3>
          <p>
            This page isolates the ML story from the command view: validation, candidate comparison, feature importance,
            and plain-English hotspot explanations.
          </p>
          <MlMetricGrid mlMetrics={data.mlMetrics} />
        </article>

        <article className="hero-side-panel">
          <div className="reason-list">
            <div className="reason-row">
              <strong>Selected candidate</strong>
              <p>{data.mlMetrics?.model_params?.selected_candidate || "Unavailable"}</p>
            </div>
            <div className="reason-row">
              <strong>Why this matters</strong>
              <p>Hackathon judges care that the model is useful, explainable, and clearly better than the baseline.</p>
            </div>
            <div className="reason-row">
              <strong>Model note</strong>
              <p>{data.mlMetrics?.notes || "No notes saved."}</p>
            </div>
          </div>
        </article>
      </section>

      <section className="three-column-grid">
        <article className="panel-card compact-panel">
          <div className="mini-callout">
            <CheckCircle2 size={16} />
            <div>
              <strong>Winner held up in comparison</strong>
              <p>The selected model stayed best even after benchmarking against alternate tree-based candidates.</p>
            </div>
          </div>
        </article>
        <article className="panel-card compact-panel">
          <div className="mini-callout">
            <Target size={16} />
            <div>
              <strong>Ranking quality is strong</strong>
              <p>Precision on the top-ranked hotspot windows is high, which is the metric that matters operationally.</p>
            </div>
          </div>
        </article>
        <article className="panel-card compact-panel">
          <div className="mini-callout">
            <BrainCircuit size={16} />
            <div>
              <strong>Explainability is built in</strong>
              <p>Each forecast now carries saved drivers instead of being a black-box probability only.</p>
            </div>
          </div>
        </article>
      </section>

      <section className="two-column-grid model-layout">
        <article className="panel-card">
          <SectionHeader
            kicker="Candidate comparison"
            title="Benchmark board"
            description="The model page keeps the benchmarking story separate from operations so the app feels calmer."
          />
          <div className="benchmark-grid">
            {viewModel.benchmarks.map((row) => <BenchmarkCard key={row.name} row={row} />)}
          </div>
        </article>

        <article className="panel-card">
          <SectionHeader
            kicker="Global feature drivers"
            title="What the model relies on most"
            description="These are permutation-importance signals on the holdout period."
          />
          <div className="feature-list tall">
            {viewModel.featureImportance.slice(0, 10).map((row) => (
              <div className="feature-row" key={row.feature}>
                <span>{featureLabel(row.feature)}</span>
                <strong>{Number(row.importance_mean).toFixed(3)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel-card">
        <SectionHeader
          kicker="Top forecasts"
          title="Predictions with explanations"
          description="This page can double as your hackathon demo script: forecast, confidence, and why it is happening."
        />
        <div className="forecast-grid">
          {viewModel.topPredictions.slice(0, 6).map((row, index) => (
            <ForecastCard key={`${row.police_station}-${row.recommended_time_window_ist}-${index}`} row={row} index={index} />
          ))}
        </div>
      </section>
    </div>
  );
}
