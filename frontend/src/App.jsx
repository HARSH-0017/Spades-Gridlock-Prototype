import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BrainCircuit, Gauge, MapPinned } from "lucide-react";
import { loadDashboardData } from "./api";
import { AppShell } from "./components/AppShell";
import { OverviewPage } from "./pages/OverviewPage";
import { OperationsPage } from "./pages/OperationsPage";
import { ModelPage } from "./pages/ModelPage";

const routes = {
  "/": OverviewPage,
  "/operations": OperationsPage,
  "/model": ModelPage,
};

function normalizePath(pathname) {
  if (!pathname || pathname === "/index.html") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

function usePathname() {
  const [pathname, setPathname] = useState(() => normalizePath(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setPathname(normalizePath(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = (nextPath) => {
    const normalized = normalizePath(nextPath);
    if (normalized === pathname) return;
    window.history.pushState({}, "", normalized);
    setPathname(normalized);
  };

  return [pathname, navigate];
}

function buildViewModel(data) {
  if (!data) {
    return {
      deployments: [],
      areasWithStatus: [],
      stations: [],
      topPredictions: [],
      featureImportance: [],
      benchmarks: [],
    };
  }

  const deploymentByArea = new Map(data.deployments.map((row) => [Number(row.area_rank), row]));
  const areasWithStatus = data.areas.map((area) => ({
    ...area,
    deployment_status: deploymentByArea.get(Number(area.area_rank))?.deployment_status || "Monitor",
  }));

  return {
    deployments: data.deployments,
    areasWithStatus,
    stations: [...new Set(areasWithStatus.map((row) => row.primary_police_station))].sort(),
    topPredictions: data.mlPredictions || [],
    featureImportance: data.mlMetrics?.model_params?.feature_importance || [],
    benchmarks: data.mlMetrics?.model_params?.benchmark_results || [],
  };
}

export function App() {
  const [pathname, navigate] = usePathname();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsRefreshing(true);
    loadDashboardData()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setIsRefreshing(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const viewModel = useMemo(() => buildViewModel(data), [data]);
  const Page = routes[pathname] || OverviewPage;

  const navigation = [
    {
      path: "/",
      label: "Overview",
      icon: Gauge,
      description: "Parking hotspots, impact proxy, and enforcement priority.",
    },
    {
      path: "/operations",
      label: "Operations",
      icon: MapPinned,
      description: "Filters, deployments, queue, and field action tables.",
    },
    {
      path: "/model",
      label: "Model",
      icon: BrainCircuit,
      description: "Validation, benchmarks, feature drivers, and ML forecasts.",
    },
  ];

  const quickStats = data
    ? [
        { label: "Hotspot areas", value: data.summary.hotspot_areas, icon: MapPinned },
        { label: "Actionable deployments", value: data.summary.deploy_count, icon: AlertTriangle },
        { label: "Model ROC-AUC", value: Number(data.mlMetrics?.roc_auc || 0).toFixed(3), icon: BrainCircuit },
      ]
    : [];

  return (
    <AppShell
      currentPath={pathname}
      navigate={navigate}
      navigation={navigation}
      quickStats={quickStats}
      summary={data?.summary}
      loading={!data && !error && isRefreshing}
      error={error}
    >
      <Page data={data} viewModel={viewModel} navigate={navigate} />
    </AppShell>
  );
}
