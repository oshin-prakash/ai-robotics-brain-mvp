import React, { useState } from "react";
import { roboticsApi } from "../services/api";
import type { SafetyStatus, SimulationState } from "../types/robotics";

interface ControlSafetyPanelProps {
  simulation: SimulationState | null;
  safety: SafetyStatus | null;
  onSimulationUpdate: (next: SimulationState) => void;
  onSafetyUpdate: (next: SafetyStatus) => void;
  onError: (msg: string) => void;
}

export const ControlSafetyPanel: React.FC<ControlSafetyPanelProps> = ({
  simulation,
  safety,
  onSimulationUpdate,
  onSafetyUpdate,
  onError,
}) => {
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const runSimAction = async (
    action: "start" | "pause" | "resume" | "reset" | "stop"
  ) => {
    setBusyAction(action);
    try {
      const updated = await roboticsApi.controlSimulation(action);
      onSimulationUpdate(updated);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Simulation action failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleEmergencyStop = async () => {
    setBusyAction("estop");
    try {
      const updated = await roboticsApi.triggerEmergencyStop(true);
      onSafetyUpdate(updated);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Emergency stop failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleClearAlerts = async () => {
    setBusyAction("clear");
    try {
      const updated = await roboticsApi.clearSafetyAlerts();
      onSafetyUpdate(updated);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to clear alerts");
    } finally {
      setBusyAction(null);
    }
  };

  const isSafe = safety?.safe ?? true;
  const isEstop = Boolean(safety?.emergency_stop);
  const alerts = safety?.active_alerts ?? [];

  return (
    <section style={{ display: "grid", gap: "1rem" }}>
      <div
        style={{
          border: "1px solid #334155",
          borderRadius: 10,
          padding: "1rem",
          background: "#0f172a",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.75rem",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Simulation Control</h2>
          <span
            style={{
              padding: "0.2rem 0.6rem",
              borderRadius: 999,
              fontSize: "0.85rem",
              background: "#1e293b",
            }}
          >
            Status: <strong>{simulation?.status ?? "unknown"}</strong>
          </span>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
          {(["start", "pause", "resume", "reset", "stop"] as const).map((action) => (
            <button
              key={action}
              type="button"
              disabled={busyAction !== null}
              onClick={() => runSimAction(action)}
              style={{
                padding: "0.45rem 0.85rem",
                borderRadius: 6,
                border: "1px solid #475569",
                background: "#1e293b",
                color: "#f8fafc",
                cursor: busyAction ? "not-allowed" : "pointer",
                textTransform: "capitalize",
              }}
            >
              {busyAction === action ? `${action}...` : action}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", gap: "1.5rem", fontSize: "0.9rem", color: "#cbd5e1" }}>
          <span>Tick: <strong>{simulation?.tick ?? "—"}</strong></span>
          <span>Sim Time: <strong>{simulation?.sim_time ?? "—"}</strong></span>
          <span>Mode: <strong>{simulation?.mode ?? "default"}</strong></span>
        </div>
      </div>

      <div
        style={{
          border: `1px solid ${!isSafe || isEstop ? "#dc2626" : "#334155"}`,
          borderRadius: 10,
          padding: "1rem",
          background: "#0f172a",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "0.75rem",
            flexWrap: "wrap",
            marginBottom: "0.75rem",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Safety Supervisor</h2>
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.9rem" }}>
              State:{" "}
              <strong style={{ color: !isSafe || isEstop ? "#f87171" : "#4ade80" }}>
                {isEstop ? "EMERGENCY STOP ACTIVE" : isSafe ? "SAFE" : "FAULT / WARNING"}
              </strong>
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleEmergencyStop}
              style={{
                padding: "0.45rem 0.85rem",
                borderRadius: 6,
                border: "none",
                background: "#dc2626",
                color: "#ffffff",
                fontWeight: 600,
                cursor: busyAction ? "not-allowed" : "pointer",
              }}
            >
              {busyAction === "estop" ? "Stopping..." : "Emergency Stop"}
            </button>
            <button
              type="button"
              disabled={busyAction !== null || alerts.length === 0}
              onClick={handleClearAlerts}
              style={{
                padding: "0.45rem 0.85rem",
                borderRadius: 6,
                border: "1px solid #475569",
                background: "#1e293b",
                color: "#f8fafc",
                cursor: busyAction || alerts.length === 0 ? "not-allowed" : "pointer",
              }}
            >
              Clear Alerts
            </button>
          </div>
        </div>

        {alerts.length === 0 ? (
          <div style={{ fontSize: "0.9rem", color: "#94a3b8" }}>No active safety alerts.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: "1.2rem", display: "grid", gap: "0.35rem" }}>
            {alerts.map((alert, idx) => (
              <li key={alert.id ?? idx} style={{ fontSize: "0.9rem", color: "#fca5a5" }}>
                [{alert.severity ?? "warning"}] {alert.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
};