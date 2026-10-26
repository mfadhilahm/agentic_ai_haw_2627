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


class CustomerDeliveryTask(EngineeringTask):
    """Session 3 customer product delivery task addressing an external product checkout."""

    task_id: str = Field(default="NW-S3-001", min_length=3, max_length=128)
    task_type: str = Field(default="customer_product_delivery", min_length=1, max_length=80)
    description: str = Field(
        default=(
            "Deliver the Nordwerk Industrie-Service Session 3 website slice "
            "(AC-01, AC-02 service N-03, AC-04) in the customer repository."
        ),
        min_length=1,
        max_length=4000,
    )
    assigned_role: str = Field(default="software_architect", min_length=1, max_length=100)
    project_id: str = Field(default="website-01", min_length=1, max_length=100)
    product_repo_path: str = Field(default="../client-01-website", min_length=1, max_length=512)
    input_files: list[str] = Field(
        default_factory=lambda: ["docs/issue-01-session-03.md", "site/index.html"]
    )
    target_product_file: str = Field(default="site/index.html", min_length=1, max_length=256)
    product_test_target: str = Field(default="tests/test_website_s3.py", min_length=1, max_length=256)
    allowed_write_prefixes: list[str] = Field(default_factory=lambda: ["site/"])
    max_correction_loops: int = Field(default=2, ge=1, le=5)
    timeout_seconds: int = Field(default=180, ge=1, le=300)


class ProductHandoverPayload(BaseModel):
    """Structured handover from Planning/Architecture capability to Implementation capability."""

    from_agent: str = "dev_architect_agent"
    from_role: str = "software_architect"
    to_role: str = "backend_api_engineer"
    project_id: str
    task_id: str
    workflow_id: str
    product_repo_path: str
    target_product_file: str = "site/index.html"
    acceptance_criteria: list[str] = Field(
        default_factory=lambda: ["AC-01", "AC-02 (N-03)", "AC-04"]
    )
    required_content: dict[str, str] = Field(default_factory=dict)
    architecture_decisions: list[str] = Field(default_factory=list)
    ready_for_implementation: bool = True


class QAHandoverPayload(BaseModel):
    """Structured handover from Implementation capability to Product QA capability."""

    from_agent: str = "dev_architect_agent"
    from_role: str = "backend_api_engineer"
    to_role: str = "qa_test_engineer"
    project_id: str
    task_id: str
    workflow_id: str
    product_repo_path: str
    modified_files: list[str] = Field(default_factory=list)
    artifact_sha256: str = ""
    product_test_target: str = "tests/test_website_s3.py"
    acceptance_criteria: list[str] = Field(
        default_factory=lambda: ["AC-01", "AC-02 (N-03)", "AC-04"]
    )
    iteration: int = 1
    ready_for_qa: bool = True


__all__ = [
    "CustomerDeliveryTask",
    "EngineeringState",
    "EngineeringTask",
    "HandoverPayload",
    "HumanGateDecision",
    "PlatformRole",
    "PlatformTask",
    "ProductHandoverPayload",
    "QAHandoverPayload",
    "QualityTask",
]
