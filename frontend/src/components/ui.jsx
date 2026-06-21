import React from "react";
import { fmt, pct, statusClass } from "../utils";

export function SectionHeader({ kicker, title, description, action }) {
  return (
    <div className="section-header">
      <div>
        <span className="eyebrow">{kicker}</span>
        <h3>{title}</h3>
        {description && <p>{description}</p>}
      </div>
      {action ? <div className="section-action">{action}</div> : null}
    </div>
  );
}

export function MetricTile({ label, value, note, tone = "default" }) {
  return (
    <article className={`metric-tile tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}

export function StoryCard({ label, title, copy }) {
  return (
    <article className="story-card">
      <span>{label}</span>
      <strong>{title}</strong>
      <p>{copy}</p>
    </article>
  );
}

export function StatusPill({ children, status }) {
  return <span className={`status-pill ${statusClass(status)}`}>{children}</span>;
}

export function CompactBarList({ rows, labelKey, valueKey, format = fmt }) {
  const selected = rows.slice(0, 5);
  const maxValue = Math.max(...selected.map((row) => Number(row[valueKey] || 0)), 1);

  return (
    <div className="compact-bars">
      {selected.map((row) => {
        const value = Number(row[valueKey] || 0);
        const width = Math.max(8, (value / maxValue) * 100);
        return (
          <div className="compact-bar-row" key={`${labelKey}-${row[labelKey]}`}>
            <div>
              <strong>{row[labelKey]}</strong>
              <span>{format(value)}</span>
            </div>
            <div className="compact-bar-track">
              <div className="compact-bar-fill" style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function MlMetricGrid({ mlMetrics }) {
  const extras = mlMetrics?.model_params?.extra_metrics || {};

  return (
    <div className="mini-metric-grid">
      <article>
        <span>Precision@20</span>
        <strong>{pct(mlMetrics?.precision_at_20)}</strong>
      </article>
      <article>
        <span>Precision@50</span>
        <strong>{pct(mlMetrics?.precision_at_50)}</strong>
      </article>
      <article>
        <span>PR-AUC</span>
        <strong>{extras.average_precision ? Number(extras.average_precision).toFixed(3) : "-"}</strong>
      </article>
      <article>
        <span>ROC-AUC</span>
        <strong>{mlMetrics?.roc_auc ? Number(mlMetrics.roc_auc).toFixed(3) : "-"}</strong>
      </article>
    </div>
  );
}
