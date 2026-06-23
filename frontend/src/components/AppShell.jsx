import React from "react";
import { Activity, ArrowRight, BrainCircuit, CalendarDays } from "lucide-react";
import { fmt } from "../utils";

function NavLink({ item, active, onNavigate }) {
  const Icon = item.icon;

  return (
    <a
      href={item.path}
      className={active ? "nav-link active" : "nav-link"}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(item.path);
      }}
    >
      <div className="nav-link-icon">
        <Icon size={16} />
      </div>
      <div className="nav-link-copy">
        <strong>{item.label}</strong>
        <span>{item.description}</span>
      </div>
      <ArrowRight size={16} />
    </a>
  );
}

export function AppShell({ currentPath, navigate, navigation, quickStats, summary, loading, error, children }) {
  const frameClass = currentPath === "/model" ? "app-frame model-route" : "app-frame";

  return (
    <div className={frameClass}>
      <aside className="sidebar-shell">
        <div className="brand-card">
          <div className="brand-mark">
            <Activity size={18} />
          </div>
          <div>
            <span className="eyebrow">Parking intelligence</span>
            <h1>ParkPulse</h1>
          </div>
        </div>

        <div className="sidebar-section">
          <span className="eyebrow">Workspace</span>
          <div className="nav-stack">
            {navigation.map((item) => (
              <NavLink
                key={item.path}
                item={item}
                active={currentPath === item.path}
                onNavigate={navigate}
              />
            ))}
          </div>
        </div>

        <div className="sidebar-section">
          <span className="eyebrow">Snapshot</span>
          <div className="sidebar-stats">
            {quickStats.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.label} className="sidebar-stat-card">
                  <div className="sidebar-stat-head">
                    <Icon size={15} />
                    <span>{item.label}</span>
                  </div>
                  <strong>{item.label === "Model ROC-AUC" ? item.value : fmt(item.value)}</strong>
                </article>
              );
            })}
          </div>
        </div>

        <div className="sidebar-highlight">
          <div className="sidebar-highlight-head">
            <CalendarDays size={15} />
            <span>Current target date</span>
          </div>
          <strong>{summary?.target_date || "Waiting for backend"}</strong>
          <p>Target dates help convert hotspot intelligence into next-day enforcement action.</p>
        </div>
      </aside>

      <main className="content-shell">
        <header className="topbar">
          <div>
            <span className="eyebrow">AI parking intelligence</span>
            <h2>Parking-induced congestion control</h2>
          </div>
          <div className="topbar-status">
            <div>
              <span>Raw records</span>
              <strong>{summary ? fmt(summary.raw_records) : "--"}</strong>
            </div>
            <div>
              <span>ML layer</span>
              <strong>{summary ? "Online" : "Loading"}</strong>
            </div>
          </div>
        </header>

        {loading && <div className="state-card">Loading workspace data...</div>}
        {error && <div className="state-card error">Unable to load dashboard: {error}</div>}
        {!loading && !error && children}
      </main>
    </div>
  );
}
