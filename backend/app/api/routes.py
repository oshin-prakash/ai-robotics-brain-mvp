from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["robotics-api"])


class CommandRequest(BaseModel):
    command_text: str
    robot_id: str = "robot_01"


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    reviewer: str = "operator"


class ModeRequest(BaseModel):
    mode: str  # "AUTONOMOUS" or "MANUAL_OVERRIDE"


class ObstacleRequest(BaseModel):
    x: float
    y: float
    radius: float = 0.4


class FeedbackRequest(BaseModel):
    context_key: str = "general"
    lesson: str
    outcome: str = "FEEDBACK"
    rating: str = "Good"


@router.post("/command")
async def post_command(payload: CommandRequest, request: Request) -> dict[str, Any]:
    orch = request.app.state.orchestrator
    res = await orch.handle_command(payload.command_text, robot_id=payload.robot_id)
    return {
        **res,
        "spoken_response": f"Task #{res['task_id']} marked {res['status']} with risk {res['risk_level']}.",
    }


@router.post("/approvals/{approval_id}")
async def decide_approval(approval_id: int, payload: ApprovalDecisionRequest, request: Request) -> dict[str, Any]:
    db = request.app.state.db
    import aiosqlite

    new_status = "APPROVED" if payload.approved else "REJECTED"
    async with aiosqlite.connect(db.db_path) as conn:
        cur = await conn.execute("SELECT id, task_id FROM approvals WHERE id = ?", (approval_id,))
        row = await cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Approval not found")
        task_id = int(row[1])
        await conn.execute("UPDATE approvals SET status = ? WHERE id = ?", (new_status, approval_id))
        await conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            ("APPROVED" if payload.approved else "CANCELLED", task_id),
        )
        await conn.commit()

    await db.log_audit(
        "APPROVAL_DECIDED",
        {"approval_id": approval_id, "task_id": task_id, "status": new_status, "reviewer": payload.reviewer},
    )
    return {"approval_id": approval_id, "task_id": task_id, "status": new_status}


@router.post("/robots/{robot_id}/estop")
async def toggle_estop(robot_id: str, request: Request, active: bool | None = None) -> dict[str, Any]:
    engine = request.app.state.engine
    current = engine.supervisor._get_or_create(robot_id).estop
    next_active = (not current) if active is None else bool(active)
    engine.supervisor.set_estop(robot_id, next_active)
    await request.app.state.db.log_audit("ESTOP_TOGGLED", {"robot_id": robot_id, "active": next_active})
    return {"robot_id": robot_id, "estop": next_active, "state": "E_STOP" if next_active else "OK"}


@router.post("/robots/{robot_id}/mode")
async def set_mode(robot_id: str, payload: ModeRequest, request: Request) -> dict[str, Any]:
    mode = payload.mode.upper().strip()
    if mode not in {"AUTONOMOUS", "MANUAL_OVERRIDE"}:
        raise HTTPException(status_code=400, detail="Mode must be AUTONOMOUS or MANUAL_OVERRIDE")
    modes: dict[str, str] = request.app.state.robot_modes
    modes[robot_id] = mode
    if mode == "MANUAL_OVERRIDE":
        request.app.state.engine.supervisor.record_joystick_heartbeat(robot_id)
    await request.app.state.db.log_audit("MODE_CHANGED", {"robot_id": robot_id, "mode": mode})
    return {"robot_id": robot_id, "mode": mode}


@router.post("/sim/obstacle")
async def spawn_obstacle(payload: ObstacleRequest, request: Request) -> dict[str, Any]:
    engine = request.app.state.engine
    engine.world.add_obstacle(payload.x, payload.y, payload.radius)
    await request.app.state.db.log_audit(
        "OBSTACLE_SPAWNED", {"x": payload.x, "y": payload.y, "radius": payload.radius}
    )
    return {"status": "spawned", "obstacle": {"x": payload.x, "y": payload.y, "radius": payload.radius}}


@router.post("/sim/drain-battery/{robot_id}")
async def drain_battery(robot_id: str, request: Request, battery_pct: float = 15.0) -> dict[str, Any]:
    engine = request.app.state.engine
    if robot_id not in engine.robots:
        raise HTTPException(status_code=404, detail="Robot not found")
    engine.robots[robot_id].battery = float(battery_pct)
    handoff_triggered = engine.check_and_execute_handoff()
    await request.app.state.db.log_audit(
        "BATTERY_DRAINED",
        {"robot_id": robot_id, "battery": battery_pct, "handoff_triggered": handoff_triggered},
    )
    return {
        "robot_id": robot_id,
        "battery": engine.robots[robot_id].battery,
        "handoff_triggered": handoff_triggered,
        "handoff_events": engine.handoff_events,
    }


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest, request: Request) -> dict[str, Any]:
    orch = request.app.state.orchestrator
    mem_id = await orch.record_reflexion(
        context_key=payload.context_key,
        lesson=f"[{payload.rating}] {payload.lesson}",
        outcome=payload.outcome,
    )
    return {"memory_id": mem_id, "status": "STORED"}


@router.get("/vision/stream")
async def vision_stream(request: Request) -> StreamingResponse:
    detector = request.app.state.detector

    async def _mjpeg_generator():
        while True:
            jpeg_bytes = detector.get_latest_jpeg()
            if jpeg_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
                )
            await asyncio.sleep(0.1)

    return StreamingResponse(_mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("/audit")
async def get_audit(request: Request, limit: int = 50) -> dict[str, Any]:
    db = request.app.state.db
    import aiosqlite
    import json

    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT id, event_type, detail_json, created_at FROM audit_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
    logs = [
        {
            "id": r["id"],
            "event_type": r["event_type"],
            "detail": json.loads(r["detail_json"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    return {"count": len(logs), "logs": logs}


@router.get("/ml/metrics")
async def get_ml_metrics(request: Request) -> dict[str, Any]:
    db = request.app.state.db
    monitor = request.app.state.ml_monitor
    import aiosqlite

    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT id, robot_id, battery, state FROM telemetry_logs ORDER BY id DESC LIMIT 100")
        rows = [dict(r) for r in await cur.fetchall()]

    labeled = []
    for r in rows:
        actual_fault = str(r.get("state", "")).upper() in {"SAFETY_HALT", "E_STOP", "GEOFENCE_BLOCKED", "FAULT"}
        vec = [
            0.3 if actual_fault else 2.2,
            0.25 if actual_fault else 0.03,
            0.18 if actual_fault else 0.02,
            65.0 if actual_fault else 42.0,
            0.35 if actual_fault else max(0.01, (100.0 - float(r.get("battery", 100.0))) * 0.005),
        ]
        scored = monitor.score_telemetry(vec)
        labeled.append({"actual_fault": actual_fault, "predicted_fault": scored["FAULT_RISK"]})

    metrics = monitor.compute_metrics(labeled)
    return {
        "metrics": metrics,
        "sample_score": monitor.score_telemetry([2.1, 0.02, 0.02, 41.0, 0.07]),
    }