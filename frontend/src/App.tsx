import { useCallback, useEffect, useState } from "react";
import { ControlSafetyPanel } from "./components/ControlSafetyPanel";
import { OrchestratorConsole } from "./components/OrchestratorConsole";
import { VisionAnomalyPanel } from "./components/VisionAnomalyPanel";
import { useRoboticsSocket } from "./hooks/useRoboticsSocket";
import { roboticsApi } from "./services/api";
import type {
  LiveStreamPayload,
  SafetyStatus,
  SimulationState,
  TelemetryAnomaly,
  VisionSnapshot,
} from "./types/robotics";

export function App() {
  const [simulation, setSimulation] = useState<SimulationState | null>(null);
  const [safety, setSafety] = useState<SafetyStatus | null>(null);
  const [vision, setVision] = useState<VisionSnapshot | null>(null);
  const [anomaly, setAnomaly] = useState<TelemetryAnomaly | null>(null);
  const [telemetry, setTelemetry] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [bannerError, setBannerError] = useState<string | null>(null);

  const loadInitialSnapshot = useCallback(async () => {
    setLoading(true);
    try {
      const [simRes, safeRes, visRes, anomRes] = await Promise.allSettled([
        roboticsApi.getSimulationState(),
        roboticsApi.getSafetyStatus(),
        roboticsApi.getLatestVision(),
        roboticsApi.getLatestAnomaly(),
      ]);

      if (simRes.status === "fulfilled") setSimulation(simRes.value);
      if (safeRes.status === "fulfilled") setSafety(safeRes.value);
      if (visRes.status === "fulfilled") setVision(visRes.value);
      if (anomRes.status === "fulfilled") setAnomaly(anomRes.value);

      const allFailed =
        simRes.status === "rejected" &&
        safeRes.status === "rejected" &&
        visRes.status === "rejected" &&
        anomRes.status === "rejected";

      if (allFailed) {
        setBannerError("Backend unreachable. Check if FastAPI server is running.");
      } else {
        setBannerError(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialSnapshot();
  }, [loadInitialSnapshot]);

  const handleStreamMessage = useCallback((payload: LiveStreamPayload) => {
    if (payload.simulation) setSimulation(payload.simulation);
    if (payload.safety) setSafety(payload.safety);
    if (payload.vision) setVision(payload.vision);
    if (payload.anomaly) setAnomaly(payload.anomaly);
    if (payload.telemetry) setTelemetry(payload.telemetry);
  }, []);

  const { status: wsStatus, lastError: wsError, reconnect } = useRoboticsSocket({
    path: "/ws/telemetry",
    enabled: true,
    onMessage: handleStreamMessage,
  });

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#020617",
        color: "#f8fafc",
        padding: "1.25rem",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div style={{ maxWidth: 1280, margin: "0 auto", display: "grid", gap: "1rem" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.75rem",
            padding: "0.9rem 1.1rem",
            borderRadius: 10,
            border: "1px solid #334155",
            background: "#0f172a",
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: "1.35rem" }}>AI Robotics Brain MVP</h1>
            <p style={{ margin: "0.2rem 0 0", fontSize: "0.85rem", color: "#94a3b8" }}>
              Simulation, Safety Supervisor, LLM Orchestrator, Vision &amp; ML Telemetry
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <span
              style={{
                padding: "0.25rem 0.65rem",
                borderRadius: 999,
                fontSize: "0.82rem",
                background: "#1e293b",
              }}
            >
              WS: <strong>{wsStatus}</strong>
            </span>
            <button
              type="button"
              onClick={() => {
                reconnect();
                loadInitialSnapshot();
              }}
              style={{
                padding: "0.35rem 0.75rem",
                borderRadius: 6,
                border: "1px solid #475569",
                background: "#1e293b",
                color: "#f8fafc",
                cursor: "pointer",
                fontSize: "0.82rem",
              }}
            >
              Refresh
            </button>
          </div>
        </header>

        {(bannerError || wsError) && (
          <div
            style={{
              padding: "0.75rem 1rem",
              borderRadius: 8,
              border: "1px solid #dc2626",
              background: "#450a0a",
              color: "#fecaca",
              fontSize: "0.88rem",
            }}
          >
            {bannerError || wsError}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
            gap: "1rem",
            alignItems: "start",
          }}
        >
          <ControlSafetyPanel
            simulation={simulation}
            safety={safety}
            onSimulationUpdate={setSimulation}
            onSafetyUpdate={setSafety}
            onError={setBannerError}
          />

          <div style={{ display: "grid", gap: "1rem" }}>
            <OrchestratorConsole onError={setBannerError} />
            <VisionAnomalyPanel
              vision={vision}
              anomaly={anomaly}
              telemetry={telemetry}
              loading={loading}
            />
          </div>
        </div>
      </div>
    </main>
  );
}

export default App;