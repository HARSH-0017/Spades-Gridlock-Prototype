const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

const withBase = (path) => `${API_BASE_URL}${path}`;

const json = async (path) => {
  const response = await fetch(withBase(path));
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json();
};

export async function loadDashboardData() {
  const [
    summary,
    areas,
    deployments,
    actions,
    stations,
    hours,
    violations,
    validation,
    shifts,
    mlMetrics,
    mlPredictions,
  ] = await Promise.all([
    json("/summary"),
    json("/hotspot-areas?limit=200"),
    json("/deployment-plan"),
    json("/action-plan?limit=200"),
    json("/station-load?limit=20"),
    json("/hourly-load"),
    json("/violation-mix?limit=10"),
    json("/validation-metrics"),
    json("/station-shift-plan?limit=20"),
    json("/ml-metrics"),
    json("/ml-predictions?limit=20"),
  ]);

  return {
    summary,
    areas,
    deployments,
    actions,
    stations,
    hours,
    violations,
    validation,
    shifts,
    mlMetrics,
    mlPredictions,
  };
}
