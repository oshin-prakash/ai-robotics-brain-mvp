import type {
  OrchestratorResponse,
  SafetyStatus,
  SimulationState,
  TelemetryAnomaly,
  VisionSnapshot,
} from "../types/robotics";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      `Request failed with status ${response.status} on ${path}`,
      response.status,
      data
    );
  }

  return data as T;
}

export const roboticsApi = {
  health: () => request<{ status: string }>("/health"),

  // Simulation controls
  getSimulationState: () => request<SimulationState>("/simulation/state"),
  controlSimulation: (action: "start" | "pause" | "resume" | "reset" | "stop") =>
    request<SimulationState>(`/simulation/${action}`, { method: "POST" }),

  // Safety supervisor
  getSafetyStatus: () => request<SafetyStatus>("/safety/status"),
  triggerEmergencyStop: (engage = true) =>
    request<SafetyStatus>("/safety/emergency-stop", {
      method: "POST",
      body: JSON.stringify({ engage }),
    }),
  clearSafetyAlerts: () =>
    request<SafetyStatus>("/safety/clear-alerts", { method: "POST" }),

  // LLM Orchestrator / command dispatch
  sendOrchestratorCommand: (prompt: string, context?: Record<string, unknown>) =>
    request<OrchestratorResponse>("/orchestrator/command", {
      method: "POST",
      body: JSON.stringify({ prompt, context }),
    }),

  // Vision worker
  getLatestVision: () => request<VisionSnapshot>("/vision/latest"),

  // ML telemetry anomaly monitor
  getLatestAnomaly: () => request<TelemetryAnomaly>("/ml/anomaly/latest"),
};