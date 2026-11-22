import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionStatus, LiveStreamPayload } from "../types/robotics";

const WS_BASE_URL = (
  import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000"
).replace(/\/+$/, "");

interface UseRoboticsSocketOptions {
  path?: string;
  enabled?: boolean;
  onMessage?: (payload: LiveStreamPayload) => void;
}

export function useRoboticsSocket(options: UseRoboticsSocketOptions = {}) {
  const { path = "/ws/telemetry", enabled = true, onMessage } = options;

  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<LiveStreamPayload | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const clearTimer = () => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  };

  const connect = useCallback(() => {
    if (!enabled) return;
    clearTimer();

    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.close();
      socketRef.current = null;
    }

    const wsUrl = `${WS_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
    setStatus("connecting");
    setLastError(null);

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as LiveStreamPayload;
        setLastMessage(parsed);
        onMessageRef.current?.(parsed);
      } catch {
        setLastError("Received non-JSON WebSocket payload");
      }
    };

    ws.onerror = () => {
      setStatus("error");
      setLastError("WebSocket connection error");
    };

    ws.onclose = () => {
      socketRef.current = null;
      if (!enabled) {
        setStatus("disconnected");
        return;
      }
      setStatus("disconnected");
      const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 10000);
      reconnectAttemptsRef.current += 1;
      reconnectTimerRef.current = window.setTimeout(() => {
        connect();
      }, delay);
    };
  }, [enabled, path]);

  const sendJson = useCallback((data: unknown) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      clearTimer();
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
        socketRef.current = null;
      }
      setStatus("disconnected");
    }

    return () => {
      clearTimer();
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connect, enabled]);

  return {
    status,
    lastMessage,
    lastError,
    sendJson,
    reconnect: connect,
  };
}