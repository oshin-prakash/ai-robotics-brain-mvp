# AI Robotics Brain MVP

A full-stack robotics telemetry and control dashboard featuring simulation controls, a safety supervisor, an LLM orchestrator console, vision worker monitoring, and ML anomaly detection—built with a FastAPI backend and a React + TypeScript + Vite frontend[cite: 2, 7, 10].

## Overview

- **Simulation Control:** Manage simulation lifecycle (`Start`, `Pause`, `Resume`, `Reset`, `Stop`) and monitor tick, simulation time, and mode[cite: 2].
- **Safety Supervisor:** Track safety state (`SAFE` / alerts), trigger emergency stops, and clear active alerts[cite: 2].
- **LLM Orchestrator Console:** Dispatch robotics tasks and commands to the orchestrator[cite: 2].
- **Vision & ML Telemetry:** View vision worker frame detections, telemetry, and ML anomaly status over REST and WebSockets[cite: 2].

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, WebSockets
- **Frontend:** React, TypeScript, Vite

## Project Structure

```text
ai-robotics-brain-mvp/
├── backend/
│   ├── app/
│   │   └── main.py
│   └── tests/
└── frontend/
    └── src/
        ├── components/
        │   ├── ControlSafetyPanel.tsx
        │   ├── OrchestratorConsole.tsx
        │   └── VisionAnomalyPanel.tsx
        ├── hooks/
        │   └── useRoboticsSocket.ts
        ├── services/
        │   └── api.ts
        ├── types/
        │   └── robotics.ts
        └── App.tsx
