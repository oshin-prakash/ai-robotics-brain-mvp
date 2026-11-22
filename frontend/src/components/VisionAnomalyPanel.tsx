import React from "react";
import type { TelemetryAnomaly, VisionSnapshot } from "../types/robotics";

interface VisionAnomalyPanelProps {
  vision: VisionSnapshot | null;
  anomaly: TelemetryAnomaly | null;
  telemetry: Record<string, unknown> | null;
  loading?: boolean;
}

export const VisionAnomalyPanel: React.FC<VisionAnomalyPanelProps> = ({
  vision,
  anomaly,
  telemetry,
  loading = false,
}) => {
  const detections = vision?.detections ?? [];
  const isAnomaly = Boolean(anomaly?.is_anomaly);
  const flaggedMetrics = anomaly?.flagged_metrics ?? [];

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
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Vision Worker</h2>
          <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Frame: <strong>{vision?.frame_id ?? "—"}</strong>
          </span>
        </div>

        {loading && detections.length === 0 ? (
          <div style={{ fontSize: "0.9rem", color: "#94a3b8" }}>
            Loading vision detections...
          </div>
        ) : detections.length === 0 ? (
          <div style={{ fontSize: "0.9rem", color: "#94a3b8" }}>
            No active vision detections.
          </div>
        ) : (
          <div style={{ display: "grid", gap: "0.5rem" }}>
            {detections.map((det, idx) => (
              <div
                key={`${det.label}-${idx}`}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "0.5rem 0.7rem",
                  borderRadius: 6,
                  background: "#020617",
                  border: "1px solid #1e293b",
                  fontSize: "0.88rem",
                }}
              >
                <strong>{det.label}</strong>
                <span style={{ color: "#cbd5e1" }}>
                  {typeof det.confidence === "number"
                    ? `${(det.confidence * 100).toFixed(1)}%`
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div
        style={{
          border: `1px solid ${isAnomaly ? "#f59e0b" : "#334155"}`,
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
            marginBottom: "0.65rem",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>ML Telemetry Anomaly Monitor</h2>
          <span
            style={{
              padding: "0.2rem 0.65rem",
              borderRadius: 999,
              fontSize: "0.82rem",
              fontWeight: 600,
              background: isAnomaly ? "#451a03" : "#052e16",
              color: isAnomaly ? "#fbbf24" : "#4ade80",
            }}
          >
            {isAnomaly ? "ANOMALY DETECTED" : "NORMAL"}
          </span>
        </div>

        <div
          style={{
            display: "flex",
            gap: "1.5rem",
            fontSize: "0.9rem",
            color: "#cbd5e1",
            marginBottom: "0.65rem",
          }}
        >
          <span>
            Score:{" "}
            <strong>
              {typeof anomaly?.score === "number" ? anomaly.score.toFixed(3) : "—"}
            </strong>
          </span>
          <span>
            Flagged:{" "}
            <strong>
              {flaggedMetrics.length > 0 ? flaggedMetrics.join(", ") : "None"}
            </strong>
          </span>
        </div>

        <div style={{ fontSize: "0.82rem", color: "#94a3b8", marginBottom: "0.35rem" }}>
          Latest Telemetry Snapshot
        </div>
        <pre
          style={{
            margin: 0,
            maxHeight: 160,
            overflowY: "auto",
            padding: "0.6rem 0.75rem",
            borderRadius: 8,
            background: "#020617",
            border: "1px solid #1e293b",
            color: "#cbd5e1",
            fontSize: "0.8rem",
          }}
        >
          {JSON.stringify(telemetry ?? {}, null, 2)}
        </pre>
      </div>
    </section>
  );
};