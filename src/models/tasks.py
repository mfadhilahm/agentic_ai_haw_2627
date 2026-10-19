"""Reusable task/state contract; independent of agent implementations."""
from __future__ import annotations

import uuid
from typing import Annotated, Literal, TypedDict

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class EngineeringTask(BaseModel):
    """Common task envelope that another team agent can import and extend."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    )
    task_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    assigned_role: str = Field(min_length=1, max_length=100)
    input_files: list[Annotated[str, Field(min_length=1, max_length=512)]] = Field(
        default_factory=list, max_length=20,
        validation_alias=AliasChoices("input_files", "artifacts"),
    )
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()), pattern=r"^[A-Za-z0-9_-]{1,100}$")


class QualityTask(EngineeringTask):
    """Quality-specific options; defaults keep existing task files usable."""

    task_type: Literal["quality_review"] = "quality_review"
    description: str = Field(default="Run regression tests and inspect selected Python files for security risks.",
                             min_length=1, max_length=4000)
    assigned_role: Literal["quality"] = "quality"
    pytest_target: str = Field(default="tests/test_quality_policy.py", min_length=1)
    timeout_seconds: int = Field(default=60, ge=1, le=300)


class EngineeringState(TypedDict, total=False):
    """Shared LangGraph state envelope; each workflow adds its result channels."""

    task: EngineeringTask
