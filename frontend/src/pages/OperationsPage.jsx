import React, { useDeferredValue, useMemo, useState } from "react";
import { Filter, Route, ShieldAlert } from "lucide-react";
import { HotspotMap } from "../views/HotspotMap";
import { SectionHeader, StatusPill } from "../components/ui";
import { fmt } from "../utils";

const defaultFilters = {
  station: "",
  status: "",
  query: "",
  limit: "25",
};

function FilterCard({ stations, filters, onChange, totalRecords, actionableCount }) {
  return (
    <article className="panel-card sticky-card">
      <SectionHeader
        kicker="Filters"
        title="Narrow the field view"
        description="Operations is focused on dispatch decisions, so filters and queue stay together on one page."
      />

      <div className="filter-form">
        <label>
          Police station
          <select value={filters.station} onChange={(event) => onChange("station", event.target.value)}>
            <option value="">All stations</option>
            {stations.map((station) => <option key={station} value={station}>{station}</option>)}
          </select>
        </label>

        <label>
          Deployment status
          <select value={filters.status} onChange={(event) => onChange("status", event.target.value)}>
            <option value="">All statuses</option>
            <option value="Deploy">Deploy</option>
            <option value="Targeted patrol">Targeted patrol</option>
            <option value="Monitor">Monitor</option>
          </select>
        </label>

        <label>
          Search junction or road
          <input
            value={filters.query}
            placeholder="Market, signal, hospital"
            onChange={(event) => onChange("query", event.target.value)}
          />
        </label>

        <label>
          Visible hotspots
          <select value={filters.limit} onChange={(event) => onChange("limit", event.target.value)}>
            <option value="15">Top 15</option>
            <option value="25">Top 25</option>
            <option value="40">Top 40</option>
            <option value="60">Top 60</option>
          </select>
        </label>
      </div>

      <button type="button" className="primary-button" onClick={() => onChange("reset", defaultFilters)}>
        Reset filters
      </button>

      <div className="filter-summary">
        <div>
          <span>Visible records</span>
          <strong>{fmt(totalRecords)}</strong>
        </div>
        <div>
          <span>Actionable rows</span>
          <strong>{fmt(actionableCount)}</strong>
        </div>
      </div>
    </article>
  );
}

function DispatchQueue({ deployments }) {
  return (
    <article className="panel-card">
      <SectionHeader
        kicker="Queue"
        title="Suggested field dispatch order"
        description="Only the top queue is shown here so the decision stays fast and uncluttered."
      />
      <div className="queue-list refined">
        {deployments.slice(0, 8).map((row, index) => (
          <article className="queue-card refined" key={`${row.area_rank}-${row.primary_police_station}`}>
            <div className="queue-rank">{String(index + 1).padStart(2, "0")}</div>
            <div className="queue-copy">
              <StatusPill status={row.deployment_status}>{row.deployment_status}</StatusPill>
              <h4>{row.primary_police_station}</h4>
              <p>{row.recommended_time_window_ist} | {row.primary_junction}</p>
              <small>{row.recommended_intervention}</small>
            </div>
            <div className="queue-meta">
              <strong>{row.suggested_patrol_units}</strong>
              <span>units</span>
            </div>
          </article>
        ))}
      </div>
    </article>
  );
}

export function OperationsPage({ data, viewModel }) {
  const [filters, setFilters] = useState(defaultFilters);
  const deferredQuery = useDeferredValue(filters.query);

  if (!data) return null;

  const visibleAreas = useMemo(() => {
    const query = deferredQuery.trim().toLowerCase();
    return viewModel.areasWithStatus
      .filter((row) => {
        const text = [
          row.primary_police_station,
          row.primary_junction,
          row.representative_location,
          row.top_violations,
          row.top_vehicle_types,
        ].join(" ").toLowerCase();

        return (
          (!filters.station || row.primary_police_station === filters.station) &&
          (!filters.status || row.deployment_status === filters.status) &&
          (!query || text.includes(query))
        );
      })
      .slice(0, Number(filters.limit));
  }, [deferredQuery, filters.limit, filters.station, filters.status, viewModel.areasWithStatus]);

  const visibleAreaRanks = useMemo(
    () => new Set(visibleAreas.map((row) => Number(row.area_rank))),
    [visibleAreas],
  );

  const visibleDeployments = useMemo(
    () => viewModel.deployments.filter((row) => visibleAreaRanks.has(Number(row.area_rank))),
    [viewModel.deployments, visibleAreaRanks],
  );

  const totalVisibleRecords = visibleAreas.reduce((sum, row) => sum + Number(row.records || 0), 0);
  const actionableCount = visibleDeployments.filter((row) => row.deployment_status !== "Monitor").length;

  const onChange = (key, value) => {
    if (key === "reset") {
      setFilters(defaultFilters);
      return;
    }
    setFilters((current) => ({ ...current, [key]: value }));
  };

  return (
    <div className="page-stack">
      <section className="operations-layout">
        <FilterCard
          stations={viewModel.stations}
          filters={filters}
          onChange={onChange}
          totalRecords={totalVisibleRecords}
          actionableCount={actionableCount}
        />

        <div className="operations-main">
          <div className="split-panels">
            <article className="panel-card panel-map">
              <SectionHeader
                kicker="Map"
                title="Filtered hotspot atlas"
                description="Operations focuses on the selected slice only, which keeps the city map readable while you filter."
              />
              <HotspotMap areas={visibleAreas} variant="atlas" />
            </article>

            <DispatchQueue deployments={visibleDeployments} />
          </div>

          <div className="split-panels">
            <article className="panel-card">
              <SectionHeader
                kicker="Deployment plan"
                title="Best current actions"
                description="Operational rows are limited so the page stays scannable."
              />
              <div className="table-wrap quiet">
                <table>
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Station</th>
                      <th>Window</th>
                      <th>Units</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleDeployments.slice(0, 12).map((row) => (
                      <tr key={`deploy-${row.area_rank}`}>
                        <td><StatusPill status={row.deployment_status}>{row.deployment_status}</StatusPill></td>
                        <td>{row.primary_police_station}</td>
                        <td>{row.recommended_time_window_ist}</td>
                        <td>{row.suggested_patrol_units}</td>
                        <td>{row.recommended_intervention}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel-card">
              <SectionHeader
                kicker="Hotspot details"
                title="Top filtered areas"
                description="Representative hotspot evidence without flooding the page."
              />
              <div className="table-wrap quiet">
                <table>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Station</th>
                      <th>Records</th>
                      <th>Impact</th>
                      <th>Main violations</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleAreas.slice(0, 12).map((row) => (
                      <tr key={`area-${row.area_rank}`}>
                        <td>{row.area_rank}</td>
                        <td>{row.primary_police_station}</td>
                        <td>{fmt(row.records)}</td>
                        <td>{Number(row.operational_impact_score_0_100).toFixed(1)}</td>
                        <td>{row.top_violations}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </div>

          <section className="three-column-grid">
            <article className="panel-card compact-panel">
              <div className="mini-callout">
                <Route size={16} />
                <div>
                  <strong>Station shift plan</strong>
                  <p>{data.shifts[0] ? `${data.shifts[0].primary_police_station} needs the heaviest shift support.` : "Shift plan unavailable."}</p>
                </div>
              </div>
            </article>
            <article className="panel-card compact-panel">
              <div className="mini-callout">
                <ShieldAlert size={16} />
                <div>
                  <strong>Action plan coverage</strong>
                  <p>{data.actions[0] ? `${data.actions[0].priority_band} priority actions are ready in the pipeline.` : "Action plan unavailable."}</p>
                </div>
              </div>
            </article>
            <article className="panel-card compact-panel">
              <div className="mini-callout">
                <Filter size={16} />
                <div>
                  <strong>Filtering philosophy</strong>
                  <p>This page intentionally hides the ML benchmark wall so dispatch decisions stay fast.</p>
                </div>
              </div>
            </article>
          </section>
        </div>
      </section>
    </div>
  );
}
