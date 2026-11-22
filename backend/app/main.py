from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.ws import ws_router
from app.brain.ml_monitor import TelemetryFaultMonitor
from app.brain.orchestrator import BrainOrchestrator
from app.db import Database
from app.sim.engine import SimulationEngine
from app.vision.detector import VisionDetector


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database()
    await db.init_db()

    engine = SimulationEngine()
    detector = VisionDetector(target_fps=12.0)
    detector.start()

    ml_monitor = TelemetryFaultMonitor()
    orchestrator = BrainOrchestrator(db=db)

    app.state.db = db
    app.state.engine = engine
    app.state.detector = detector
    app.state.ml_monitor = ml_monitor
    app.state.orchestrator = orchestrator
    app.state.robot_modes = {"robot_01": "AUTONOMOUS", "robot_02": "AUTONOMOUS"}

    await db.log_audit("APP_STARTED", {"status": "ok"})
    try:
        yield
    finally:
        detector.stop()


app = FastAPI(title="AI Robotics Brain MVP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)