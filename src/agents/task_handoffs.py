"""Optional adapter: existing QA agent consumes the common Session 2 task."""

from __future__ import annotations

from typing import Any

from src.agents.qa_test_agent import QATestRequest, QATestResult, run_qa_agent
from src.agents.task_models import EngineeringTask


def run_qa_engineering_task(task: EngineeringTask, *, pytest_target: str,
                            timeout_seconds: int = 60, **kwargs: Any) -> QATestResult:
    """Use exactly the same EngineeringTask contract as ops-agent.

    The current QA agent remains responsible for its own results/traces.
    """
    if task.assigned_role != "qa_test_engineer":
        raise ValueError("Engineering task is not assigned to QA")
    return run_qa_agent(QATestRequest(task_id=task.task_id, pytest_target=pytest_target,
                                      timeout_seconds=timeout_seconds), **kwargs)
