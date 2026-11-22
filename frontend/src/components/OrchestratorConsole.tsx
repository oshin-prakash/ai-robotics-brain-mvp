import React, { useState } from "react";
import { roboticsApi } from "../services/api";
import type { OrchestratorResponse } from "../types/robotics";

interface CommandEntry {
  id: string;
  prompt: string;
  response: OrchestratorResponse;
  timestamp: string;
}

interface OrchestratorConsoleProps {
  onError: (msg: string) => void;
}

export const OrchestratorConsole: React.FC<OrchestratorConsoleProps> = ({
  onError,
}) => {
  const [prompt, setPrompt] = useState("");
  const [sending, setSending] = useState(false);
  const [history, setHistory] = useState<CommandEntry[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || sending) return;

    setSending(true);
    try {
      const response = await roboticsApi.sendOrchestratorCommand(trimmed);
      setHistory((prev) => [
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          prompt: trimmed,
          response,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev,
      ]);
      setPrompt("");
    } catch (err) {
      onError(
        err instanceof Error ? err.message : "Failed to dispatch orchestrator command"
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <section
      style={{
        border: "1px solid #334155",
        borderRadius: 10,
        padding: "1rem",
        background: "#0f172a",
        display: "grid",
        gap: "0.85rem",
      }}
    >
      <h2 style={{ margin: 0, fontSize: "1.1rem" }}>LLM Orchestrator Console</h2>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem" }}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter robotics task or command (e.g., Inspect waypoint A)..."
          disabled={sending}
          style={{
            flex: 1,
            padding: "0.55rem 0.75rem",
            borderRadius: 6,
            border: "1px solid #475569",
            background: "#020617",
            color: "#f8fafc",
          }}
        />
        <button
          type="submit"
          disabled={sending || !prompt.trim()}
          style={{
            padding: "0.55rem 1rem",
            borderRadius: 6,
            border: "none",
            background: "#2563eb",
            color: "#ffffff",
            fontWeight: 600,
            cursor: sending || !prompt.trim() ? "not-allowed" : "pointer",
          }}
        >
          {sending ? "Sending..." : "Dispatch"}
        </button>
      </form>

      <div style={{ display: "grid", gap: "0.6rem", maxHeight: 280, overflowY: "auto" }}>
        {history.length === 0 ? (
          <div style={{ fontSize: "0.9rem", color: "#94a3b8" }}>
            No orchestrator commands sent yet.
          </div>
        ) : (
          history.map((item) => (
            <div
              key={item.id}
              style={{
                border: "1px solid #1e293b",
                borderRadius: 8,
                padding: "0.65rem 0.75rem",
                background: "#020617",
                fontSize: "0.88rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.35rem" }}>
                <strong>Prompt: {item.prompt}</strong>
                <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>{item.timestamp}</span>
              </div>
              <pre
                style={{
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  color: "#cbd5e1",
                  fontSize: "0.82rem",
                }}
              >
                {JSON.stringify(item.response, null, 2)}
              </pre>
            </div>
          ))
        )}
      </div>
    </section>
  );
};