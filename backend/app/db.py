from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "robotics_brain.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_id TEXT NOT NULL,
    command_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    risk_level TEXT NOT NULL DEFAULT 'LOW',
    plan_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'AWAITING_APPROVAL',
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS episodic_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_key TEXT NOT NULL,
    lesson TEXT NOT NULL,
    outcome TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_id TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    theta REAL NOT NULL,
    battery REAL NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    async def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA_SQL)
            await db.commit()

    async def create_task(
        self,
        robot_id: str,
        command_text: str,
        status: str = "PENDING",
        risk_level: str = "LOW",
        plan: list[dict[str, Any]] | None = None,
    ) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO tasks (robot_id, command_text, status, risk_level, plan_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (robot_id, command_text, status, risk_level, json.dumps(plan or []), _utc_now()),
            )
            await db.commit()
            return int(cur.lastrowid)

    async def create_approval(self, task_id: int, reason: str, status: str = "AWAITING_APPROVAL") -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO approvals (task_id, reason, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, reason, status, _utc_now()),
            )
            await db.commit()
            return int(cur.lastrowid)

    async def add_memory(self, context_key: str, lesson: str, outcome: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO episodic_memories (context_key, lesson, outcome, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (context_key, lesson, outcome, _utc_now()),
            )
            await db.commit()
            return int(cur.lastrowid)

    async def get_recent_memories(self, limit: int = 5) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT id, context_key, lesson, outcome, created_at FROM episodic_memories ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def log_telemetry(
        self,
        robot_id: str,
        x: float,
        y: float,
        theta: float,
        battery: float,
        state: str,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO telemetry_logs (robot_id, x, y, theta, battery, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (robot_id, x, y, theta, battery, state, _utc_now()),
            )
            await db.commit()

    async def log_audit(self, event_type: str, detail: dict[str, Any]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO audit_logs (event_type, detail_json, created_at) VALUES (?, ?, ?)",
                (event_type, json.dumps(detail), _utc_now()),
            )
            await db.commit()