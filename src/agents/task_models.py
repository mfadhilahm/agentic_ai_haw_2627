"""Shared task contract for Session 2 agent-to-agent handovers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EngineeringTask(BaseModel):
    task_id: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    task_type: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    assigned_role: str = Field(min_length=2, max_length=80)
    input_files: list[str] = Field(default_factory=list, max_length=60)
    workflow_id: str | None = Field(default=None, max_length=120)
