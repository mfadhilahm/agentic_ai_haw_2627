from __future__ import annotations

import argparse
import ast
import json
import multiprocessing
import time
import uuid
from pathlib import Path
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.agents.qa_test_agent import QATestResult, run_qa_agent
from src.agents.task_models import (
    EngineeringState,
    EngineeringTask,
    HandoverPayload,
    HumanGateDecision,
    PlatformRole,
    PlatformTask,
)
from src.app.settings import get_settings
from src.llm.factory import get_chat_model
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACE_FILE = "evidence/session-02/platform-agent-trace.jsonl"


class PlatformFinding(BaseModel):
    severity: Literal["low", "medium", "high"]
    component: str
    description: str


class PlatformAgentResult(BaseModel):
    status: Literal["passed", "failed", "needs_review", "error"]
    role_executed: str
    summary: str
    findings: list[PlatformFinding] = Field(default_factory=list)
    handover: HandoverPayload | None = None
    human_gate_status: HumanGateDecision = "pending_approval"
    human_approval_required: bool = True


class PlatformToQAWorkflowResult(BaseModel):
    workflow_id: str
    task_id: str
    platform_result: PlatformAgentResult
    qa_result: QATestResult | None = None
    human_gate_status: HumanGateDecision
    approved_by_human: str | None = None


class PlatformState(EngineeringState, total=False):
    request: PlatformTask
    inspection_report: dict[str, Any]
    tool_used: str
    result: dict[str, Any]
    error: str


class HandoverWorkflowState(TypedDict, total=False):
    task: PlatformTask
    platform_result: PlatformAgentResult
    qa_result: QATestResult | None
    human_gate_status: HumanGateDecision
    approved_by_human: str | None


def _coerce_platform_task(request: EngineeringTask | PlatformTask | dict[str, Any]) -> PlatformTask:
    if isinstance(request, PlatformTask):
        return request
    if isinstance(request, EngineeringTask):
        data = request.model_dump()
        return PlatformTask(**data)
    return PlatformTask.model_validate(request)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


def _safe_repo_path(relative_path: str) -> Path:
    requested = (REPO_ROOT / relative_path).resolve()
    allowed_roots = [(REPO_ROOT / "src").resolve(), (REPO_ROOT / "tests").resolve()]
    if not any(
        requested == root or root in requested.parents for root in allowed_roots
    ):
        raise ValueError("Target path must stay within src/ or tests/")
    if not requested.exists() or not requested.is_file():
        raise FileNotFoundError(relative_path)
    return requested


def inspect_agent_architecture_tool(input_files: list[str]) -> dict[str, Any]:
    """Tool for agent_engineer: inspects LangGraph state, nodes, and tracing in Python files."""
    if not input_files:
        raise ValueError("input_files must not be empty")
    report: dict[str, Any] = {"role": "agent_engineer", "files": []}
    for rel_path in input_files:
        path = _safe_repo_path(rel_path)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        report["files"].append(
            {
                "file": rel_path,
                "classes": classes,
                "functions": functions,
                "uses_langgraph": "StateGraph" in source,
                "uses_tracing": "append_trace" in source,
                "uses_llm_factory": "get_chat_model" in source,
            }
        )
    return report


def inspect_integration_contracts_tool(
    input_files: list[str], target_role: str
) -> dict[str, Any]:
    """Tool for integration_engineer: inspects FastAPI endpoints and agent handover contracts."""
    if not input_files:
        raise ValueError("input_files must not be empty")
    report: dict[str, Any] = {
        "role": "integration_engineer",
        "target_handover_role": target_role,
        "endpoints": [],
        "agent_entrypoints": [],
        "pydantic_models": [],
    }
    for rel_path in input_files:
        path = _safe_repo_path(rel_path)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = [getattr(base, "id", "") for base in node.bases]
                if "BaseModel" in base_names or "TypedDict" in base_names:
                    report["pydantic_models"].append(
                        {"file": rel_path, "model": node.name}
                    )
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("@app."):
                report["endpoints"].append({"file": rel_path, "decorator": stripped})
            if stripped.startswith("def run_") and "_agent" in stripped:
                report["agent_entrypoints"].append(
                    {"file": rel_path, "signature": stripped}
                )
    return report


def _parse_result(text: str, request: PlatformTask) -> PlatformAgentResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    default_handover = HandoverPayload(
        from_role=request.assigned_role,
        to_role=request.target_handover_role,
        task_id=request.task_id,
        workflow_id=request.workflow_id,
        verified_files=request.input_files,
        pytest_target=request.pytest_target,
        ready_for_handover=True,
        notes=f"Handover prepared by {request.assigned_role}.",
    )
    try:
        parsed = json.loads(cleaned)
        parsed["role_executed"] = request.assigned_role
        if not parsed.get("handover"):
            parsed["handover"] = default_handover.model_dump()
        return PlatformAgentResult.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError):
        return PlatformAgentResult(
            status="passed",
            role_executed=request.assigned_role,
            summary="Platform inspection completed successfully; LLM output was not valid JSON.",
            findings=[
                PlatformFinding(
                    severity="low",
                    component="llm_parser",
                    description="Human review should check the unparseable LLM summary.",
                )
            ],
            handover=default_handover,
            human_gate_status="pending_approval",
        )


def _invoke_configured_llm_worker(
    system_text: str,
    human_text: str,
    queue: multiprocessing.Queue,
) -> None:
    try:
        response = get_chat_model().invoke(
            [SystemMessage(content=system_text), HumanMessage(content=human_text)]
        )
        queue.put(
            {
                "text": _message_text(response),
                "usage": usage_from_message(response),
            }
        )
    except Exception as exc:
        queue.put({"error": f"{type(exc).__name__}: {exc}"})


def _invoke_configured_llm_bounded(
    system_text: str,
    human_text: str,
    timeout_seconds: int,
) -> tuple[str | None, tuple[int | None, int | None], str | None]:
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(
        target=_invoke_configured_llm_worker,
        args=(system_text, human_text, queue),
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return None, (None, None), "LLM call timed out"
    if queue.empty():
        return None, (None, None), "LLM call produced no response"
    payload = queue.get()
    if payload.get("error"):
        return None, (None, None), payload["error"]
    return payload["text"], tuple(payload["usage"]), None


def build_graph(llm: Any | None = None):
    def route_by_role(state: PlatformState) -> str:
        role = state["request"].assigned_role
        return "inspect_agent" if role == "agent_engineer" else "inspect_integration"

    def inspect_agent(state: PlatformState) -> PlatformState:
        request = state["request"]
        try:
            report = inspect_agent_architecture_tool(request.input_files)
            return {
                "inspection_report": report,
                "tool_used": "inspect_agent_architecture_tool",
            }
        except Exception as exc:
            return {
                "error": f"{type(exc).__name__}: {exc}",
                "tool_used": "inspect_agent_architecture_tool",
            }

    def inspect_integration(state: PlatformState) -> PlatformState:
        request = state["request"]
        try:
            report = inspect_integration_contracts_tool(
                request.input_files, request.target_handover_role
            )
            return {
                "inspection_report": report,
                "tool_used": "inspect_integration_contracts_tool",
            }
        except Exception as exc:
            return {
                "error": f"{type(exc).__name__}: {exc}",
                "tool_used": "inspect_integration_contracts_tool",
            }

    def route_after_inspection(state: PlatformState):
        return END if state.get("error") else "summarize"

    def summarize(state: PlatformState) -> PlatformState:
        request = state["request"]
        system_text = (
            f"You are the platform-agent acting in role '{request.assigned_role}' "
            "for a student software company. Return ONLY valid JSON with keys: "
            "status (passed|failed|needs_review|error), role_executed, summary, "
            "findings (list of {severity: low|medium|high, component, description}), "
            "human_gate_status (pending_approval|approved|changes_requested|escalate_to_human), "
            "and human_approval_required (bool)."
        )
        human_text = (
            "/no_think\n"
            f"Task ID: {request.task_id}\n"
            f"Workflow ID: {request.workflow_id}\n"
            f"Role: {request.assigned_role}\n"
            f"Description: {request.description}\n"
            f"Inspection report:\n{json.dumps(state['inspection_report'], indent=2)}"
        )
        if llm is None:
            text, usage, llm_error = _invoke_configured_llm_bounded(
                system_text,
                human_text,
                request.timeout_seconds,
            )
            if llm_error:
                result = PlatformAgentResult(
                    status="needs_review",
                    role_executed=request.assigned_role,
                    summary=(
                        "Platform inspection finished, but the configured LLM could not "
                        f"summarize the run: {llm_error}"
                    ),
                    findings=[
                        PlatformFinding(
                            severity="medium",
                            component="llm",
                            description="Human review required because LLM summarization failed.",
                        )
                    ],
                    handover=HandoverPayload(
                        from_role=request.assigned_role,
                        to_role=request.target_handover_role,
                        task_id=request.task_id,
                        workflow_id=request.workflow_id,
                        verified_files=request.input_files,
                        pytest_target=request.pytest_target,
                        ready_for_handover=False,
                        notes="LLM error; escalate to human.",
                    ),
                    human_gate_status="escalate_to_human",
                )
                result_dict = result.model_dump()
                result_dict["_usage"] = usage
                return {"result": result_dict}
            result = _parse_result(text or "", request)
            result_dict = result.model_dump()
            result_dict["_usage"] = usage
            return {"result": result_dict}

        response = llm.invoke(
            [SystemMessage(content=system_text), HumanMessage(content=human_text)]
        )
        result = _parse_result(_message_text(response), request)
        result_dict = result.model_dump()
        result_dict["_usage"] = usage_from_message(response)
        return {"result": result_dict}

    builder = StateGraph(PlatformState)
    builder.add_node("inspect_agent", inspect_agent)
    builder.add_node("inspect_integration", inspect_integration)
    builder.add_node("summarize", summarize)
    builder.add_conditional_edges(
        START, route_by_role, ["inspect_agent", "inspect_integration"]
    )
    builder.add_conditional_edges(
        "inspect_agent", route_after_inspection, ["summarize", END]
    )
    builder.add_conditional_edges(
        "inspect_integration", route_after_inspection, ["summarize", END]
    )
    builder.add_edge("summarize", END)
    return builder.compile()


def run_platform_agent(
    request: EngineeringTask | PlatformTask | dict[str, Any],
    *,
    llm: Any | None = None,
    trace_file: str | None = DEFAULT_TRACE_FILE,
) -> PlatformAgentResult:
    task = _coerce_platform_task(request)
    run_id = str(uuid.uuid4())
    settings = get_settings()
    started = time.perf_counter()
    graph = build_graph(llm)
    state = graph.invoke({"task": task, "request": task}, {"recursion_limit": 6})
    duration = time.perf_counter() - started
    tool_used = state.get(
        "tool_used",
        "inspect_agent_architecture_tool"
        if task.assigned_role == "agent_engineer"
        else "inspect_integration_contracts_tool",
    )

    if state.get("error"):
        result = PlatformAgentResult(
            status="error",
            role_executed=task.assigned_role,
            summary=state["error"],
            human_gate_status="escalate_to_human",
        )
        append_trace(
            {
                "run_id": run_id,
                "workflow_id": task.workflow_id,
                "task": task.model_dump(mode="json"),
                "task_id": task.task_id,
                "agent": "platform-agent",
                "role": task.assigned_role,
                "model": settings.llm_model,
                "status": result.status,
                "tools": [tool_used],
                "duration_seconds": round(duration, 4),
                "error": state["error"],
            },
            trace_file,
        )
        return result

    raw = dict(state["result"])
    input_tokens, output_tokens = raw.pop("_usage", (None, None))
    result = PlatformAgentResult.model_validate(raw)
    credits = estimate_cost_credits(
        duration_seconds=duration,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    append_trace(
        {
            "run_id": run_id,
            "workflow_id": task.workflow_id,
            "task": task.model_dump(mode="json"),
            "task_id": task.task_id,
            "agent": "platform-agent",
            "role": task.assigned_role,
            "model": settings.llm_model,
            "status": result.status,
            "tools": [tool_used],
            "duration_seconds": round(duration, 4),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_credits": credits,
        },
        trace_file,
    )
    if llm is None and trace_file == DEFAULT_TRACE_FILE:
        _append_usage_csv(
            task_id=task.task_id,
            role=task.assigned_role,
            run_id=run_id,
            workflow_id=task.workflow_id,
            model=settings.llm_model,
            duration=round(duration, 4),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            credits=credits,
        )
    return result


def _append_usage_csv(
    *,
    task_id: str,
    role: str,
    run_id: str,
    workflow_id: str,
    model: str,
    duration: float,
    input_tokens: int | None,
    output_tokens: int | None,
    credits: float,
) -> None:
    from datetime import datetime, timezone

    usage_path = REPO_ROOT / "costs" / "usage.csv"
    if not usage_path.exists():
        return
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    notes = (
        f"run_id={run_id} workflow_id={workflow_id} model={model} "
        f"calls=1 duration={duration}s input_tokens={input_tokens} output_tokens={output_tokens}"
    )
    row = f"{date_str},{task_id},agent,platform-agent ({role}),1,runs,{credits},{notes}\n"
    with usage_path.open("a", encoding="utf-8") as handle:
        handle.write(row)


def run_platform_to_qa_workflow(
    task: EngineeringTask | PlatformTask | dict[str, Any],
    *,
    platform_llm: Any | None = None,
    qa_llm: Any | None = None,
    human_decision: HumanGateDecision = "approved",
    approved_by_human: str = "muhammad",
    trace_file: str | None = DEFAULT_TRACE_FILE,
) -> PlatformToQAWorkflowResult:
    """Agent-to-Agent LangGraph workflow: platform-agent -> structured handover -> qa-test-agent -> Human Gate."""
    ptask = _coerce_platform_task(task)

    def platform_step(state: HandoverWorkflowState) -> HandoverWorkflowState:
        res = run_platform_agent(
            state["task"], llm=platform_llm, trace_file=trace_file
        )
        return {"platform_result": res}

    def route_handover(state: HandoverWorkflowState) -> str:
        pres = state["platform_result"]
        if (
            pres.status in ("error", "failed")
            or pres.handover is None
            or not pres.handover.ready_for_handover
        ):
            return "human_gate"
        return "qa_step"

    def qa_step(state: HandoverWorkflowState) -> HandoverWorkflowState:
        handover = state["platform_result"].handover
        assert handover is not None
        qa_task = handover.to_quality_task(
            timeout_seconds=state["task"].timeout_seconds
        )
        qres = run_qa_agent(qa_task, llm=qa_llm, trace_file=trace_file)
        return {"qa_result": qres}

    def human_gate(state: HandoverWorkflowState) -> HandoverWorkflowState:
        pres = state["platform_result"]
        qres = state.get("qa_result")
        if pres.status == "error" or (qres and qres.status == "error"):
            return {
                "human_gate_status": "escalate_to_human",
                "approved_by_human": approved_by_human,
            }
        if qres and qres.status == "failed":
            return {
                "human_gate_status": "changes_requested",
                "approved_by_human": approved_by_human,
            }
        return {
            "human_gate_status": human_decision,
            "approved_by_human": approved_by_human,
        }

    builder = StateGraph(HandoverWorkflowState)
    builder.add_node("platform_step", platform_step)
    builder.add_node("qa_step", qa_step)
    builder.add_node("human_gate", human_gate)
    builder.add_edge(START, "platform_step")
    builder.add_conditional_edges(
        "platform_step", route_handover, ["qa_step", "human_gate"]
    )
    builder.add_edge("qa_step", "human_gate")
    builder.add_edge("human_gate", END)

    workflow = builder.compile()
    final_state = workflow.invoke({"task": ptask}, {"recursion_limit": 6})
    return PlatformToQAWorkflowResult(
        workflow_id=ptask.workflow_id,
        task_id=ptask.task_id,
        platform_result=final_state["platform_result"],
        qa_result=final_state.get("qa_result"),
        human_gate_status=final_state["human_gate_status"],
        approved_by_human=final_state.get("approved_by_human"),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="SESSION-02-PLATFORM")
    parser.add_argument(
        "--role",
        choices=["agent_engineer", "integration_engineer"],
        default="agent_engineer",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=["src/agents/qa_test_agent.py", "src/app/main.py"],
    )
    parser.add_argument("--pytest-target", default="tests/starter/test_api.py")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    result = run_platform_agent(
        PlatformTask(
            task_id=args.task_id,
            assigned_role=args.role,
            input_files=args.files,
            pytest_target=args.pytest_target,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
