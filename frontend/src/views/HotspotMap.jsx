import React from "react";
import { useEffect, useRef } from "react";
import L from "leaflet";
import { fmt, impactBand } from "../utils";

export function HotspotMap({ areas, variant = "card" }) {
  const mapRef = useRef(null);
  const nodeRef = useRef(null);
  const layerRef = useRef(null);

  useEffect(() => {
    if (!nodeRef.current || mapRef.current) return;

    mapRef.current = L.map(nodeRef.current, {
      zoomControl: true,
      scrollWheelZoom: true,
      attributionControl: variant !== "atlas",
    }).setView([12.9716, 77.5946], 11);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap",
    }).addTo(mapRef.current);

    layerRef.current = L.layerGroup().addTo(mapRef.current);
  }, []);

  useEffect(() => {
    if (!mapRef.current || !layerRef.current || !areas.length) return;

    layerRef.current.clearLayers();
    const maxRecords = Math.max(...areas.map((area) => Number(area.records)));
    const bounds = [];

    areas.forEach((area) => {
      const lat = Number(area.center_lat);
      const lon = Number(area.center_lon);
      const band = impactBand(area.operational_impact_score_0_100);
      const radius = 8 + (Number(area.records) / maxRecords) * 22;

      L.circleMarker([lat, lon], {
        radius,
        color: "#0f172a",
        weight: 1.5,
        fillColor: band.color,
        fillOpacity: 0.74,
      })
        .bindPopup(`
          <div class="popup-title">${area.area_rank}. ${area.primary_police_station}</div>
          <div class="popup-line"><b>Impact:</b> ${Number(area.operational_impact_score_0_100).toFixed(1)}</div>
          <div class="popup-line"><b>Records:</b> ${fmt(area.records)}</div>
          <div class="popup-line"><b>Window:</b> ${area.recommended_time_window_ist}</div>
          <div class="popup-line"><b>Junction:</b> ${area.primary_junction}</div>
        `)
        .addTo(layerRef.current);

      bounds.push([lat, lon]);
    });

    mapRef.current.fitBounds(bounds, { padding: [28, 28], maxZoom: 14 });
    setTimeout(() => mapRef.current.invalidateSize(), 80);
  }, [areas]);

  return (
    <div className={variant === "atlas" ? "atlas-map-shell" : "map-card"}>
      <div ref={nodeRef} className="leaflet-map" />
      <div className="map-legend">
        <div><span style={{ background: "#dc2626" }} />Critical impact</div>
        <div><span style={{ background: "#ea580c" }} />High impact</div>
        <div><span style={{ background: "#2563eb" }} />Medium impact</div>
        <div><span style={{ background: "#0f766e" }} />Watch list</div>
      </div>
    </div>
  );
}
