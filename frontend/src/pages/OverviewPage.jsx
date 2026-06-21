import React from "react";
import { AlertTriangle, BrainCircuit, Clock3, MapPinned } from "lucide-react";
import { HotspotMap } from "../views/HotspotMap";
import { CompactBarList, MetricTile, MlMetricGrid, SectionHeader, StoryCard } from "../components/ui";
import { fmt, pct } from "../utils";

function HeroRecommendation({ leadDeployment, leadPrediction }) {
  return (
    <section className="hero-grid">
      <article className="hero-card">
        <span className="eyebrow">Primary recommendation</span>
        <h3>
          {leadDeployment
            ? `${leadDeployment.primary_police_station} | ${leadDeployment.recommended_time_window_ist}`
            : "No deployment recommendation available"}
        </h3>
        <p>
          {leadDeployment
            ? `${leadDeployment.recommended_intervention} near ${leadDeployment.primary_junction}. Allocate ${leadDeployment.suggested_patrol_units} units and monitor repeat obstruction.`
            : "Wait for the backend pipeline to finish or review the operations page."}
        </p>
        {leadPrediction?.features?.risk_summary ? (
          <div className="hero-callout">{leadPrediction.features.risk_summary}</div>
        ) : null}
      </article>

      <article className="hero-side-panel">
        <span className="eyebrow">Why now</span>
        <div className="reason-list">
          {(leadPrediction?.features?.risk_drivers || []).slice(0, 3).map((driver) => (
            <div key={driver.feature} className="reason-row">
              <strong>{driver.label}</strong>
              <p>{driver.detail}</p>
            </div>
          ))}
          {!leadPrediction?.features?.risk_drivers?.length && (
            <div className="reason-row">
              <strong>Model explanation pending</strong>
              <p>Restart the backend on the newest build to expose the saved risk drivers.</p>
            </div>
          )}
        </div>
      </article>
    </section>
  );
}

export function OverviewPage({ data, viewModel, navigate }) {
  if (!data) return null;

  const leadDeployment = viewModel.deployments[0];
  const leadPrediction = viewModel.topPredictions[0];
  const featuredAreas = viewModel.areasWithStatus.slice(0, 10);

  return (
    <div className="page-stack">
      <HeroRecommendation leadDeployment={leadDeployment} leadPrediction={leadPrediction} />

      <section className="metric-row">
        <MetricTile
          label="Hotspot areas"
          value={fmt(data.summary.hotspot_areas)}
          note={`${fmt(featuredAreas.length)} featured on the overview map`}
          tone="teal"
        />
        <MetricTile
          label="Deploy now"
          value={fmt(data.summary.deploy_count)}
          note={`${fmt(data.summary.suggested_units)} suggested citywide patrol units`}
          tone="amber"
        />
        <MetricTile
          label="Top impact score"
          value={Number(data.summary.top_impact_score || 0).toFixed(1)}
          note={`${featuredAreas[0]?.primary_police_station || "No station"} currently leads`}
          tone="orange"
        />
        <MetricTile
          label="Top model confidence"
          value={leadPrediction ? pct(leadPrediction.ml_risk_probability) : "-"}
          note={leadPrediction ? `${leadPrediction.police_station} at ${leadPrediction.recommended_time_window_ist}` : "No ML forecast loaded"}
          tone="blue"
        />
      </section>

      <section className="two-column-grid">
        <div className="panel-card panel-map">
          <SectionHeader
            kicker="City map"
            title="Where pressure is most concentrated"
            description="Overview uses only the highest-value hotspots, so the map stays readable instead of becoming a pin cloud."
            action={<button className="ghost-button" type="button" onClick={() => navigate("/operations")}>Open operations</button>}
          />
          <HotspotMap areas={featuredAreas} variant="atlas" />
        </div>

        <div className="panel-stack">
          <article className="panel-card">
            <SectionHeader
              kicker="Model snapshot"
              title="ML quality at a glance"
              description="Ranking quality matters most for field deployment, so overview shows only the core validation signals."
            />
            <MlMetricGrid mlMetrics={data.mlMetrics} />
          </article>

          <article className="panel-card">
            <SectionHeader
              kicker="Operations story"
              title="What the city is telling us"
              description="Quick narrative cards for a fast executive read."
            />
            <div className="story-grid compact">
              <StoryCard
                label="Peak hour"
                title={data.hours[0]?.time_window_ist || "-"}
                copy={data.hours[0] ? `${fmt(data.hours[0].records)} records in the busiest time band.` : "Hourly mix not available."}
              />
              <StoryCard
                label="Dominant violation"
                title={data.violations[0]?.violation_label || "-"}
                copy={data.violations[0] ? `${fmt(data.violations[0].records)} records carry this label.` : "Violation mix unavailable."}
              />
              <StoryCard
                label="Lead station"
                title={data.stations[0]?.police_station || "-"}
                copy={data.stations[0] ? `${fmt(data.stations[0].records)} raw records, highest station burden.` : "Station ranking unavailable."}
              />
            </div>
          </article>
        </div>
      </section>

      <section className="three-column-grid">
        <article className="panel-card">
          <SectionHeader kicker="Station load" title="Busiest stations" />
          <CompactBarList rows={data.stations} labelKey="police_station" valueKey="records" />
        </article>
        <article className="panel-card">
          <SectionHeader kicker="Time pressure" title="Peak hour windows" />
          <CompactBarList rows={data.hours} labelKey="time_window_ist" valueKey="records" />
        </article>
        <article className="panel-card">
          <SectionHeader kicker="Violation mix" title="What keeps repeating" />
          <CompactBarList rows={data.violations} labelKey="violation_label" valueKey="records" />
        </article>
      </section>

      <section className="page-footer-strip">
        <article className="page-footer-card">
          <MapPinned size={18} />
          <div>
            <strong>Use overview for briefings</strong>
            <p>Keep this page open when you need a clean story for judges, mentors, or officials.</p>
          </div>
        </article>
        <article className="page-footer-card">
          <Clock3 size={18} />
          <div>
            <strong>Use operations for action</strong>
            <p>Switch to the operations page when you want to filter, shortlist, and dispatch.</p>
          </div>
        </article>
        <article className="page-footer-card">
          <BrainCircuit size={18} />
          <div>
            <strong>Use model for trust</strong>
            <p>Benchmark comparisons and ML explanations live separately so they do not crowd the command view.</p>
          </div>
        </article>
      </section>
    </div>
  );
}
