import React from "react";
import { BrainCircuit, Gauge, Route } from "lucide-react";
import { HotspotMap } from "../views/HotspotMap";
import { CompactBarList, MetricTile, SectionHeader, StatusPill } from "../components/ui";
import { fmt, pct } from "../utils";

function ImpactSummary({ leadArea, leadDeployment, leadPrediction, navigate }) {
  return (
    <section className="impact-summary-panel">
      <div className="impact-summary-copy">
        <span className="eyebrow">Problem focus</span>
        <h3>Illegal parking hotspots ranked by likely traffic-flow impact</h3>
        <p>
          This view answers the challenge directly: detect recurring parking clusters, estimate carriageway/intersection
          obstruction risk, and prioritize enforcement zones.
        </p>
        <button className="primary-button" type="button" onClick={() => navigate("/operations")}>
          Open enforcement workspace
        </button>
      </div>

      <div className="impact-answer-grid">
        <div>
          <span>Top hotspot</span>
          <strong>{leadArea ? `${leadArea.primary_police_station} #${leadArea.area_rank}` : "-"}</strong>
          <p>{leadArea?.primary_junction || "Waiting for hotspot data"}</p>
        </div>
        <div>
          <span>Impact proxy</span>
          <strong>{leadArea ? Number(leadArea.operational_impact_score_0_100).toFixed(1) : "-"}</strong>
          <p>Recurrence, severity, obstruction risk, station burden, and time window.</p>
        </div>
        <div>
          <span>Field action</span>
          <strong>{leadDeployment?.deployment_status || "Monitor"}</strong>
          <p>
            {leadDeployment
              ? `${leadDeployment.suggested_patrol_units} units | ${leadDeployment.recommended_time_window_ist}`
              : "No deployment row available"}
          </p>
        </div>
        <div>
          <span>ML signal</span>
          <strong>{leadPrediction ? pct(leadPrediction.ml_risk_probability) : "-"}</strong>
          <p>{leadPrediction?.features?.risk_summary || "Next-day risk appears after model output is loaded."}</p>
        </div>
      </div>

    </section>
  );
}

function PriorityTable({ rows }) {
  return (
    <div className="table-wrap quiet">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Station</th>
            <th>Likely choke point</th>
            <th>Window</th>
            <th>Impact</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 8).map((row) => (
            <tr key={`impact-${row.area_rank}`}>
              <td>{row.area_rank}</td>
              <td>{row.primary_police_station}</td>
              <td>{row.primary_junction || row.representative_location}</td>
              <td>{row.recommended_time_window_ist}</td>
              <td>{Number(row.operational_impact_score_0_100).toFixed(1)}</td>
              <td><StatusPill status={row.deployment_status}>{row.deployment_status}</StatusPill></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OverviewPage({ data, viewModel, navigate }) {
  if (!data) return null;

  const impactAreas = viewModel.areasWithStatus.slice(0, 12);
  const leadArea = impactAreas[0];
  const leadDeployment = viewModel.deployments[0];
  const leadPrediction = viewModel.topPredictions[0];
  const deployRows = viewModel.deployments.filter((row) => row.deployment_status !== "Monitor");
  const topDeploymentRecords = deployRows.reduce((sum, row) => sum + Number(row.historical_area_records || 0), 0);

  return (
    <div className="page-stack">
      <ImpactSummary
        leadArea={leadArea}
        leadDeployment={leadDeployment}
        leadPrediction={leadPrediction}
        navigate={navigate}
      />

      <section className="two-column-grid impact-map-layout">
        <article className="panel-card panel-map">
          <SectionHeader
            kicker="Heatmap answer"
            title="Where illegal parking is most likely to hurt traffic flow"
            description="Marker size shows violation volume; color shows the congestion-impact proxy used for prioritization."
            action={<button className="ghost-button" type="button" onClick={() => navigate("/operations")}>Filter zones</button>}
          />
          <HotspotMap areas={impactAreas} variant="atlas" />
        </article>

        <article className="panel-card priority-panel">
          <SectionHeader
            kicker="Priority list"
            title="Enforcement zones to act on first"
            description="Hotspot rank, likely choke point, time window, and action status."
          />
          <PriorityTable rows={impactAreas} />
        </article>
      </section>

      <section className="metric-row">
        <MetricTile
          label="Violation records"
          value={fmt(data.summary.raw_records)}
          note="Parking violation evidence available for hotspot detection."
          tone="teal"
        />
        <MetricTile
          label="Priority zones"
          value={fmt(data.summary.deploy_count)}
          note={`${fmt(data.summary.suggested_units)} patrol units recommended for targeted action.`}
          tone="amber"
        />
        <MetricTile
          label="Impact ceiling"
          value={Number(data.summary.top_impact_score || 0).toFixed(1)}
          note="Highest congestion-impact proxy score in the current hotspot table."
          tone="orange"
        />
        <MetricTile
          label="Next-day ML risk"
          value={leadPrediction ? pct(leadPrediction.ml_risk_probability) : "-"}
          note={leadPrediction ? `${leadPrediction.police_station} | ${leadPrediction.recommended_time_window_ist}` : "ML forecast not loaded."}
          tone="blue"
        />
      </section>

      <section className="three-column-grid">
        <article className="panel-card">
          <SectionHeader kicker="Commercial and station burden" title="Busiest stations" />
          <CompactBarList rows={data.stations} labelKey="police_station" valueKey="records" />
        </article>
        <article className="panel-card">
          <SectionHeader kicker="Time-flow conflict" title="Peak violation windows" />
          <CompactBarList rows={data.hours} labelKey="time_window_ist" valueKey="records" />
        </article>
        <article className="panel-card">
          <SectionHeader kicker="Obstruction signal" title="Repeating violation types" />
          <CompactBarList rows={data.violations} labelKey="violation_label" valueKey="records" />
        </article>
      </section>

      <section className="page-footer-strip">
        <article className="page-footer-card">
          <Gauge size={18} />
          <div>
            <strong>Impact is the first lens</strong>
            <p>The landing page starts with hotspot-to-congestion prioritization, matching the problem statement.</p>
          </div>
        </article>
        <article className="page-footer-card">
          <Route size={18} />
          <div>
            <strong>{fmt(topDeploymentRecords)} records covered</strong>
            <p>Current deploy and targeted-patrol rows cover the highest-value historical hotspots.</p>
          </div>
        </article>
        <article className="page-footer-card">
          <BrainCircuit size={18} />
          <div>
            <strong>Model page explains trust</strong>
            <p>Validation, benchmarks, and forecast drivers remain available as a separate page.</p>
          </div>
        </article>
      </section>
    </div>
  );
}
