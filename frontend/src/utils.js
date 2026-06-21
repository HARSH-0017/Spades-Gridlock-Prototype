export const fmt = (value) => Number(value || 0).toLocaleString("en-IN");

export const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;

export function impactBand(score) {
  const value = Number(score);
  if (value >= 70) return { label: "Critical", className: "critical", color: "#dc2626" };
  if (value >= 62) return { label: "High", className: "high", color: "#ea580c" };
  if (value >= 54) return { label: "Medium", className: "medium", color: "#2563eb" };
  return { label: "Watch", className: "watch", color: "#0f766e" };
}

export function statusClass(status) {
  if (status === "Deploy") return "deploy";
  if (status === "Targeted patrol") return "high";
  return "watch";
}

export function filterRows(rows, filters) {
  const query = filters.query.trim().toLowerCase();
  return rows
    .filter((row) => {
      const text = Object.values(row).join(" ").toLowerCase();
      return (
        (!filters.station || row.primary_police_station === filters.station) &&
        (!filters.status || row.deployment_status === filters.status || !row.deployment_status) &&
        (!query || text.includes(query))
      );
    })
    .slice(0, Number(filters.limit));
}
