from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.models.tasks import EngineeringState, EngineeringTask, QualityTask

PlatformRole = Literal["agent_engineer", "integration_engineer"]
HumanGateDecision = Literal[
    "pending_approval", "approved", "changes_requested", "escalate_to_human"
]


class PlatformTask(EngineeringTask):
    """Platform-specific options extending the shared EngineeringTask from src/models/tasks.py."""

    task_type: str = Field(default="platform_check", min_length=1, max_length=80)
    description: str = Field(
        default="Inspect LangGraph agent architecture and integration contracts.",
        min_length=1,
        max_length=4000,
    )
    assigned_role: str = Field(default="agent_engineer", min_length=1, max_length=100)
    input_files: list[str] = Field(
        default_factory=lambda: ["src/agents/qa_test_agent.py", "src/app/main.py"]
    )
    pytest_target: str = Field(default="tests/starter/test_api.py", min_length=1)
    target_handover_role: str = Field(default="quality")
    timeout_seconds: int = Field(default=180, ge=1, le=300)


class HandoverPayload(BaseModel):
    """Structured handover payload from platform-agent to QA/Quality agent."""

    from_agent: str = "platform-agent"
    from_role: str
    to_role: str
    task_id: str
    workflow_id: str
    verified_files: list[str] = Field(default_factory=list)
    pytest_target: str = "tests/starter/test_api.py"
    ready_for_handover: bool = True
    notes: str = ""

    def to_quality_task(self, timeout_seconds: int = 60) -> QualityTask:
        return QualityTask(
            task_id=self.task_id,
            workflow_id=self.workflow_id,
            description=self.notes or f"Handover from {self.from_role} to {self.to_role}",
            input_files=self.verified_files or ["src/app/main.py"],
            pytest_target=self.pytest_target,
            timeout_seconds=min(timeout_seconds, 300),
        )


__all__ = [
    "EngineeringState",
    "EngineeringTask",
    "HandoverPayload",
    "HumanGateDecision",
    "PlatformRole",
    "PlatformTask",
    "QualityTask",
]
