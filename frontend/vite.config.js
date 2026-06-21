import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiRoutes = [
  "/health",
  "/summary",
  "/hotspot-areas",
  "/deployment-plan",
  "/station-load",
  "/action-plan",
  "/hourly-load",
  "/station-shift-plan",
  "/violation-mix",
  "/validation-metrics",
  "/ml-metrics",
  "/ml-predictions",
];

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      apiRoutes.map((route) => [
        route,
        {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      ]),
    ),
  },
});
