from __future__ import annotations

import json
import os
from typing import Any

from app.brain.schemas import (
    BrainPlanOutput,
    NavigateToZoneCall,
    ReturnToDockCall,
    ScanSurroundingsCall,
    SpeakResponseCall,
    TriggerHandoffCall,
)
from app.db import Database

HIGH_RISK_ZONES = {"restricted_lab", "high_fault_area"}


class BrainOrchestrator:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

    def _rule_based_plan(self, command_text: str, robot_id: str = "robot_01") -> BrainPlanOutput:
        text = command_text.lower().strip()
        risk: str = "LOW"
        steps: list[Any] = []

        if "restricted_lab" in text or "restricted" in text or "high-fault" in text or "high fault" in text:
            risk = "HIGH"
            steps.append(
                NavigateToZoneCall(
                    zone="restricted_lab",
                    robot_id=robot_id,
                    allow_restricted=True,
                )
            )
        elif "dock" in text:
            steps.append(ReturnToDockCall(robot_id=robot_id))
        elif "handoff" in text:
            steps.append(TriggerHandoffCall(reason=command_text))
        elif "scan" in text:
            steps.append(ScanSurroundingsCall(robot_id=robot_id))
        else:
            zone = "station_a"
            for candidate in ("station_a", "station_b", "charge_pad", "dock"):
                if candidate in text:
                    zone = candidate
                    break
            steps.append(NavigateToZoneCall(zone=zone, robot_id=robot_id))

        steps.append(SpeakResponseCall(text=f"Planned {len(steps)} step(s) for: {command_text}"))
        return BrainPlanOutput(risk_level=risk, rationale="Rule-based planner fallback", steps=steps)  # type: ignore[arg-type]

    async def generate_plan(self, command_text: str, robot_id: str = "robot_01") -> BrainPlanOutput:
        memories = await self.db.get_recent_memories(limit=5)
        if not self.api_key:
            return self._rule_based_plan(command_text, robot_id=robot_id)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            memory_context = "\n".join(
                f"- [{m['outcome']}] {m['context_key']}: {m['lesson']}" for m in memories
            )
            resp = await client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Return JSON matching {\"risk_level\": \"LOW|MEDIUM|HIGH\", "
                            "\"rationale\": str, \"steps\": [{\"tool\": ...}]}. "
                            "Tools: navigate_to_zone(zone, robot_id, allow_restricted), "
                            "scan_surroundings(robot_id), return_to_dock(robot_id), "
                            "trigger_handoff(reason, from_robot, to_robot), speak_response(text). "
                            "Mark risk_level HIGH for restricted_lab or high-fault areas.\n"
                            f"Recent lessons:\n{memory_context}"
                        ),
                    },
                    {"role": "user", "content": command_text},
                ],
                temperature=0.1,
            )
            raw = resp.choices[0].message.content or "{}"
            return BrainPlanOutput.model_validate(json.loads(raw))
        except Exception:
            return self._rule_based_plan(command_text, robot_id=robot_id)

    async def handle_command(self, command_text: str, robot_id: str = "robot_01") -> dict[str, Any]:
        plan = await self.generate_plan(command_text, robot_id=robot_id)
        targets_restricted = any(
            getattr(s, "zone", "") in HIGH_RISK_ZONES for s in plan.steps
        )
        risk_level = "HIGH" if (plan.risk_level == "HIGH" or targets_restricted) else plan.risk_level

        plan_dicts = [s.model_dump() for s in plan.steps]
        status = "AWAITING_APPROVAL" if risk_level == "HIGH" else "APPROVED"

        task_id = await self.db.create_task(
            robot_id=robot_id,
            command_text=command_text,
            status=status,
            risk_level=risk_level,
            plan=plan_dicts,
        )

        approval_id: int | None = None
        if status == "AWAITING_APPROVAL":
            approval_id = await self.db.create_approval(
                task_id=task_id,
                reason=f"High-risk command requires operator approval: {command_text}",
                status="AWAITING_APPROVAL",
            )

        await self.db.log_audit(
            "TASK_ORCHESTRATED",
            {"task_id": task_id, "status": status, "risk_level": risk_level, "approval_id": approval_id},
        )

        return {
            "task_id": task_id,
            "approval_id": approval_id,
            "status": status,
            "risk_level": risk_level,
            "steps": plan_dicts,
        }

    async def record_reflexion(self, context_key: str, lesson: str, outcome: str = "FAILURE") -> int:
        mem_id = await self.db.add_memory(context_key=context_key, lesson=lesson, outcome=outcome)
        await self.db.log_audit("REFLEXION_STORED", {"memory_id": mem_id, "context_key": context_key, "outcome": outcome})
        return mem_id