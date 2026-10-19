from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

HumanGateDecision = Literal[
    "pending_approval", "approved", "changes_requested", "escalate_to_human"
]


class EngineeringTask(BaseModel):
    """Shared technical task model used across multiple team agents (Session 2, Task 3)."""

    task_id: str = Field(min_length=3)
    workflow_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    task_type: str = Field(default="platform_check", min_length=1)
    description: str = Field(
        default="Inspect LangGraph agent architecture and integration contracts."
    )
    assigned_role: str = Field(default="agent_engineer", min_length=1)
    input_files: list[str] = Field(
        default_factory=lambda: ["src/agents/qa_test_agent.py", "src/app/main.py"]
    )
    pytest_target: str = Field(default="tests/starter/test_api.py", min_length=1)
    target_handover_role: str = Field(default="qa_test_engineer")
    timeout_seconds: int = Field(default=180, ge=1, le=900)


class HandoverPayload(BaseModel):
    """Structured handover payload between agents."""

    from_agent: str = "platform-agent"
    from_role: str
    to_role: str
    task_id: str
    workflow_id: str
    verified_files: list[str] = Field(default_factory=list)
    pytest_target: str = "tests/starter/test_api.py"
    ready_for_handover: bool = True
    notes: str = ""

    def to_engineering_task(self, description: str = "") -> EngineeringTask:
        return EngineeringTask(
            task_id=self.task_id,
            workflow_id=self.workflow_id,
            task_type="handover_verification",
            description=description or self.notes or f"Handover from {self.from_role} to {self.to_role}",
            assigned_role=self.to_role,
            input_files=self.verified_files or [self.pytest_target],
            pytest_target=self.pytest_target,
        )
