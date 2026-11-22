from __future__ import annotations

from typing import Literal, Union
from pydantic import BaseModel, Field


class NavigateToZoneCall(BaseModel):
    tool: Literal["navigate_to_zone"] = "navigate_to_zone"
    zone: str = Field(..., min_length=1)
    robot_id: str = "robot_01"
    allow_restricted: bool = False


class ScanSurroundingsCall(BaseModel):
    tool: Literal["scan_surroundings"] = "scan_surroundings"
    robot_id: str = "robot_01"


class ReturnToDockCall(BaseModel):
    tool: Literal["return_to_dock"] = "return_to_dock"
    robot_id: str = "robot_01"


class TriggerHandoffCall(BaseModel):
    tool: Literal["trigger_handoff"] = "trigger_handoff"
    reason: str = Field(..., min_length=1)
    from_robot: str = "robot_01"
    to_robot: str = "robot_02"


class SpeakResponseCall(BaseModel):
    tool: Literal["speak_response"] = "speak_response"
    text: str = Field(..., min_length=1)


ToolCall = Union[
    NavigateToZoneCall,
    ScanSurroundingsCall,
    ReturnToDockCall,
    TriggerHandoffCall,
    SpeakResponseCall,
]


class BrainPlanOutput(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    rationale: str = ""
    steps: list[ToolCall] = Field(default_factory=list)