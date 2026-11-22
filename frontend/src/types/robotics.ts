export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface SimulationState {
  status: "idle" | "running" | "paused" | "stopped";
  tick?: number;
  sim_time?: number;
  mode?: string;
}

export interface SafetyAlert {
  id?: string;
  severity?: "info" | "warning" | "critical";
  message: string;
  timestamp?: string;
}

export interface SafetyStatus {
  safe: boolean;
  emergency_stop?: boolean;
  active_alerts?: SafetyAlert[];
}

export interface TelemetryAnomaly {
  is_anomaly: boolean;
  score?: number;
  flagged_metrics?: string[];
  timestamp?: string;
  details?: Record<string, unknown>;
}

export interface VisionDetection {
  label: string;
  confidence?: number;
  bbox?: number[];
  timestamp?: string;
}

export interface VisionSnapshot {
  frame_id?: string | number;
  detections: VisionDetection[];
  timestamp?: string;
}

export interface OrchestratorResponse {
  command?: string;
  plan?: unknown;
  status?: string;
  message?: string;
  data?: Record<string, unknown>;
}

export interface LiveStreamPayload {
  type?: string;
  timestamp?: string;
  simulation?: SimulationState;
  safety?: SafetyStatus;
  telemetry?: Record<string, unknown>;
  anomaly?: TelemetryAnomaly;
  vision?: VisionSnapshot;
}