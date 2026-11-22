# AI Robotics Brain MVP - Master Engineering Specification

## 1. Core Architectural Laws (NEVER VIOLATE)
- Decouple Brain from Control: The LLM Planner NEVER outputs raw motor velocities. It outputs validated Pydantic tool calls (`navigate_to_zone`, `scan_surroundings`, `inspect_zone`, `return_to_dock`, `handoff_to_robot`).
- Deterministic Safety First: `backend/app/sim/safety.py` runs every simulation tick (20 Hz) and sits AFTER path planning and manual input. It MUST enforce:
  1. E-STOP latch overrides everything (`vx = 0, omega = 0`).
  2. LIDAR min distance < 0.45m in forward arc -> immediate halt + `SAFETY_HALT` alert.
  3. Restricted Zone polygon entry -> immediate block unless human approval token exists.
  4. Hard velocity clamp: `|vx| <= 1.2 m/s`, `|omega| <= 2.0 rad/s`.
- Adapter Pattern: All simulator interactions go through `RobotAdapter` interface so Phase 2 can swap in ROS 2 without changing `brain/` or `api/`.
- Graceful Fallbacks:
  - If `LLM_API_KEY` is missing or fails, provide a deterministic rule-based intent parser fallback so the demo NEVER crashes.
  - If no webcam is detected by OpenCV, generate a clean synthetic annotated test frame so VisionFeed NEVER crashes.

## 2. World Coordinate System & Named Zones
- Arena dimensions: `10.0m x 8.0m` (origin `0,0` at top-left).
- Named Zones:
  - `dock`: `(1.0, 1.0)`
  - `office`: `(2.5, 6.0)`
  - `storage_north`: `(8.0, 1.5)`
  - `loading_bay`: `(8.2, 6.2)`
  - `restricted_lab`: rectangle `x: [4.2, 6.2], y: [3.0, 5.0]` (HIGH RISK - requires human approval)
- Two Robots: `robot_01` starts at `(1.0, 1.0)` battery 85%; `robot_02` starts at `(1.0, 2.2)` battery 95%.

## 3. Shared State Machine
Robot states: `IDLE`, `PLANNING`, `AWAITING_APPROVAL`, `EXECUTING`, `MANUAL_OVERRIDE`, `FAULT_RECOVERY`, `E_STOP`.

## 4. Coding Standards
- Backend: Python 3.11+, full type hints, async FastAPI, clean logging, zero hardcoded secrets.
- Frontend: React + TypeScript + Tailwind CSS, clean dark-slate engineering UI, no external CSS files.
- Always write at least 1 pytest verification test per backend module before declaring a step done.