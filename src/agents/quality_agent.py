"""Quality workflow: pytest agent -> security checker -> human review gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from src.agents.qa_test_agent import QATestResult, run_qa_agent
from src.agents.quality_support import source_version, write_json
from src.agents.security_agent import SecurityResult, run_security_agent
from src.models.tasks import EngineeringState, EngineeringTask, QualityTask


class QualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: QualityTask
    qa: QATestResult
    security: SecurityResult
    status: Literal["awaiting_human_review", "blocked"]
    human_approval_required: Literal[True] = True
    human_decision: Literal["pending"] = "pending"
    created_at: str
    source_version: dict[str, Any]


class QualityState(EngineeringState, total=False):
    qa: dict[str, Any]
    security: dict[str, Any]
    report: dict[str, Any]


def build_quality_graph(*, llm: Any | None = None, trace_file: str | None = None):
    def qa_node(state: QualityState) -> QualityState:
        task = cast(QualityTask, state["task"])
        return {"qa": run_qa_agent(task, llm=llm, trace_file=trace_file).model_dump()}

    def security_node(state: QualityState) -> QualityState:
        task = state["task"]
        return {"security": run_security_agent(task, trace_file=trace_file,
            qa_result=state["qa"]).model_dump()}

    def human_gate(state: QualityState) -> QualityState:
        qa, security = QATestResult.model_validate(state["qa"]), SecurityResult.model_validate(state["security"])
        ready = qa.status == "passed" and security.status == "passed"
        report = QualityReport(task=state["task"], qa=qa, security=security,
            status="awaiting_human_review" if ready else "blocked",
            created_at=datetime.now(timezone.utc).isoformat(), source_version=source_version())
        # There is deliberately no automatic approval/deployment edge.
        return {"report": report.model_dump()}

    graph = StateGraph(QualityState)
    graph.add_node("qa", qa_node)
    graph.add_node("security", security_node)
    graph.add_node("human_gate", human_gate)
    graph.add_edge(START, "qa")
    graph.add_edge("qa", "security")
    graph.add_edge("security", "human_gate")
    graph.add_edge("human_gate", END)
    return graph.compile()


def run_quality_agent(task: EngineeringTask | dict[str, Any], *, llm: Any | None = None,
                      trace_file: str | None = None) -> QualityReport:
    if isinstance(task, EngineeringTask) and not isinstance(task, QualityTask):
        task = task.model_dump()
    task = QualityTask.model_validate(task)
    state = build_quality_graph(llm=llm, trace_file=trace_file).invoke(
        {"task": task}, {"recursion_limit": 6})
    return QualityReport.model_validate(state["report"])


def record_human_review(report_path: Path, *, reviewer: str, decision: str) -> Path:
    """Record a user's explicit CLI decision, bound to the exact report bytes.

    Identity is self-declared on this local trusted CLI, not authenticated.
    No model invokes this function, and it does not deploy anything.
    """
    if not reviewer.strip() or decision not in {"approved", "changes_requested", "escalate_to_human"}:
        raise ValueError("A reviewer and a supported explicit decision are required")
    contents = report_path.read_bytes()
    report = QualityReport.model_validate_json(contents)
    if decision == "approved":
        if report.status != "awaiting_human_review":
            raise ValueError("Blocked checks require correction and a new run before approval")
        if source_version()["source_sha256"] != report.source_version.get("source_sha256"):
            raise ValueError("Sources changed since the run; run the checks again")
    review_path = report_path.with_name(report_path.stem + ".review-" + uuid.uuid4().hex + ".json")
    write_json(review_path, {
        "task_id": report.task.task_id, "workflow_id": report.task.workflow_id,
        "reviewer": reviewer.strip(), "decision": decision,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "report_path": str(report_path.resolve()),
        "report_sha256": hashlib.sha256(contents).hexdigest(),
        "artifact_sha256": report.security.artifact_sha256,
        "identity_assurance": "self_declared_local_cli",
    })
    return review_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Run checks and stop at the human gate")
    run.add_argument("--task-file", type=Path, help="Structured JSON task from a human or another agent")
    run.add_argument("--task-id", default="SESSION-02-QUALITY")
    run.add_argument("--pytest-target", default="tests/test_quality_policy.py")
    run.add_argument("--timeout-seconds", type=int, default=60)
    run.add_argument("--artifact", action="append", default=None)
    run.add_argument("--trace-file", default=None)
    run.add_argument("--report", type=Path)
    review = commands.add_parser("review", help="Record an explicit human decision about a saved report")
    review.add_argument("--report", type=Path, required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--decision", choices=["approved", "changes_requested", "escalate_to_human"], required=True)
    args = parser.parse_args()
    if args.command == "review":
        print(record_human_review(args.report, reviewer=args.reviewer, decision=args.decision))
        return
    task = QualityTask.model_validate_json(args.task_file.read_bytes()) if args.task_file else QualityTask(
        task_id=args.task_id, pytest_target=args.pytest_target, timeout_seconds=args.timeout_seconds,
        input_files=args.artifact if args.artifact is not None else ["src/app/main.py"])
    report = run_quality_agent(task, trace_file=args.trace_file)
    report_path = args.report or Path("logs") / f"{task.workflow_id}.report.json"
    write_json(report_path, report.model_dump())
    print(report.model_dump_json(indent=2))
    print(f"Report: {report_path.resolve()}")
    # Zero means checks passed and human review is pending, never human approval.
    raise SystemExit(0 if report.status == "awaiting_human_review" else 1)


if __name__ == "__main__":
    main()
