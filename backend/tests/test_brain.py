import pytest
from pydantic import ValidationError

from app.brain.orchestrator import BrainOrchestrator
from app.brain.schemas import BrainPlanOutput
from app.db import Database


def test_pydantic_rejects_invalid_tool() -> None:
    with pytest.raises(ValidationError):
        BrainPlanOutput.model_validate(
            {
                "risk_level": "LOW",
                "rationale": "Invalid tool test",
                "steps": [{"tool": "launch_missiles", "target": "mars"}],
            }
        )


@pytest.mark.asyncio
async def test_high_risk_command_pauses_in_awaiting_approval(tmp_path) -> None:
    db = Database(tmp_path / "brain_test.db")
    await db.init_db()
    orchestrator = BrainOrchestrator(db=db)

    result = await orchestrator.handle_command("Go to restricted_lab immediately", robot_id="robot_01")
    assert result["risk_level"] == "HIGH"
    assert result["status"] == "AWAITING_APPROVAL"
    assert result["approval_id"] is not None


@pytest.mark.asyncio
async def test_reflexion_episodic_memory_is_stored_and_retrieved(tmp_path) -> None:
    db = Database(tmp_path / "brain_memory.db")
    await db.init_db()
    orchestrator = BrainOrchestrator(db=db)

    await orchestrator.record_reflexion(
        context_key="navigate_to_zone:station_b",
        lesson="Rack obstacle near y=4.2 blocks direct straight path; use A* waypoints.",
        outcome="BLOCKED_PATH",
    )
    memories = await db.get_recent_memories(limit=5)
    assert len(memories) == 1
    assert "A* waypoints" in memories[0]["lesson"]