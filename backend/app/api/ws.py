from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.sim.sensors import raycast_lidar
from app.sim.world import VelocityCmd

ws_router = APIRouter(tags=["telemetry-ws"])


@ws_router.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    app = websocket.app
    engine = app.state.engine
    detector = app.state.detector
    modes: dict[str, str] = app.state.robot_modes

    async def _receiver() -> None:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "manual_cmd":
                robot_id = str(msg.get("robot_id", "robot_01"))
                vx = float(msg.get("vx", 0.0))
                omega = float(msg.get("omega", 0.0))
                engine.supervisor.record_joystick_heartbeat(robot_id)
                engine.tick(robot_id=robot_id, cmd=VelocityCmd(vx=vx, vy=0.0, omega=omega), manual_mode=True)

    recv_task = asyncio.create_task(_receiver())

    try:
        while True:
            robots_payload: dict[str, Any] = {}
            lidar_payload: dict[str, Any] = {}

            for rid, r in engine.robots.items():
                scan = raycast_lidar(engine.world, r.pose)
                robots_payload[rid] = {
                    "robot_id": rid,
                    "x": r.pose.x,
                    "y": r.pose.y,
                    "theta": r.pose.theta,
                    "battery": r.battery,
                    "paused": r.paused,
                    "task_active": r.task_active,
                    "mode": modes.get(rid, "AUTONOMOUS"),
                }
                lidar_payload[rid] = {
                    "angles_rad": scan.angles_rad,
                    "ranges_m": scan.ranges_m,
                }

            payload = {
                "type": "telemetry_tick",
                "arena": {
                    "width_m": engine.world.width_m,
                    "height_m": engine.world.height_m,
                    "obstacles": engine.world.obstacles,
                },
                "robots": robots_payload,
                "lidar": lidar_payload,
                "slam_grid": engine.world.slam_grid.tolist(),
                "detections": detector.get_latest_detections(),
                "alerts": {
                    rid: st.alerts[-5:]
                    for rid, st in engine.supervisor.robots.items()
                },
                "handoff_events": engine.handoff_events[-5:],
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.1)  # 10 Hz stream
    except WebSocketDisconnect:
        pass
    finally:
        recv_task.cancel()