from __future__ import annotations

import argparse
import json
import multiprocessing
import time
import uuid
from pathlib import Path
from typing import Any, Literal, TypedDict

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError

from src.app.settings import get_settings
from src.llm.factory import get_chat_model
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLES_FILE = REPO_ROOT / "organization" / "roles.yaml"
DEFAULT_TRACE_FILE = "evidence/session-02/dev-architect-agent-trace.jsonl"

RoleType = Literal["software_architect", "backend_api_engineer"]

# Universal sandbox boundaries: secrets, VCS internals, and starter assessment exclusions
PROTECTED_PATH_PREFIXES = (".git/",)
STARTER_EXCLUSION_PREFIXES = ("examples/", "tests/starter/")


class RoleMetadata(BaseModel):
    role_id: str
    title: str
    responsibility: str
    agent_id: str
    accountable_human: str
    human_approval_required: bool = True


DEFAULT_ROLE_METADATA: dict[str, RoleMetadata] = {
    "software_architect": RoleMetadata(
        role_id="software_architect",
        title="Software Architect",
        responsibility="System architecture, interfaces, ADRs, technical standards",
        agent_id="sa-agent",
        accountable_human="unspecified",
        human_approval_required=True,
    ),
    "backend_api_engineer": RoleMetadata(
        role_id="backend_api_engineer",
        title="Backend / API Engineer",
        responsibility="Backend services, business logic, API contracts",
        agent_id="bae-agent",
        accountable_human="unspecified",
        human_approval_required=True,
    ),
}


def load_role_metadata(role_id: str, roles_path: Path = ROLES_FILE) -> RoleMetadata:
    """Load role configuration dynamically from organization/roles.yaml."""
    fallback = DEFAULT_ROLE_METADATA.get(
        role_id,
        RoleMetadata(
            role_id=role_id,
            title=role_id.replace("_", " ").title(),
            responsibility="Engineering analysis and implementation",
            agent_id=f"{role_id}-agent",
            accountable_human="unspecified",
        ),
    )
    if not roles_path.is_file():
        return fallback

    try:
        raw_data = yaml.safe_load(roles_path.read_text(encoding="utf-8")) or {}
        for entry in raw_data.get("roles", []):
            if isinstance(entry, dict) and entry.get("id") == role_id:
                target_actor = str(entry.get("target_actor") or "")
                parts = [p.strip() for p in target_actor.split(",") if p.strip()]
                agent_candidates = [p for p in parts if "agent" in p.lower()]
                agent_id = (
                    agent_candidates[0]
                    if agent_candidates
                    else (parts[-1] if parts else fallback.agent_id)
                )
                raw_approval = entry.get("human_approval_required", True)
                approval_bool = raw_approval if isinstance(raw_approval, bool) else True
                return RoleMetadata(
                    role_id=role_id,
                    title=str(entry.get("title") or fallback.title),
                    responsibility=str(
                        entry.get("responsibility") or fallback.responsibility
                    ),
                    agent_id=agent_id,
                    accountable_human=str(
                        entry.get("accountable_human") or fallback.accountable_human
                    ),
                    human_approval_required=approval_bool,
                )
    except Exception:
        return fallback

    return fallback


class DevArchitectRequest(BaseModel):
    """Input model for the Developer & Architect Agent (compatible with shared EngineeringTask)."""

    task_id: str = Field(min_length=3)
    task_type: str = Field(default="feature", min_length=1)
    description: str = Field(min_length=5)
    assigned_role: RoleType = "backend_api_engineer"
    input_files: list[str] = Field(default_factory=list)
    output_artifact_path: str | None = Field(default=None)
    timeout_seconds: int = Field(default=60, ge=1, le=300)


class ProposedFileChange(BaseModel):
    file_path: str
    action: Literal["create", "modify", "delete"]
    description: str
    code_snippet: str = ""


class DevArchitectResult(BaseModel):
    """Structured output produced by the Developer & Architect Agent."""

    task_id: str
    role: RoleType
    agent: str
    status: Literal["completed", "needs_review", "error"]
    summary: str
    decisions_or_contracts: list[str] = Field(default_factory=list)
    proposed_changes: list[ProposedFileChange] = Field(default_factory=list)
    written_artifact_path: str | None = None
    human_approval_required: bool = True


class DevArchitectState(TypedDict, total=False):
    request: DevArchitectRequest
    role_meta: RoleMetadata
    file_contents: dict[str, str]
    tools_used: list[str]
    result: dict[str, Any]
    error: str


def _normalize_rel_path(target: Path) -> str:
    return str(target.relative_to(REPO_ROOT)).replace("\\", "/")


def _validate_repo_path(relative_path: str, *, for_write: bool = False) -> Path:
    if not relative_path or not relative_path.strip():
        raise ValueError("File path must not be empty")

    requested = (REPO_ROOT / relative_path).resolve()
    try:
        requested.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path escapes repository root: {relative_path}") from exc

    rel_norm = _normalize_rel_path(requested)
    name = requested.name

    # Never allow access to environment secret files or VCS internals
    if (
        name.startswith(".env")
        or rel_norm == ".git"
        or any(rel_norm.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES)
    ):
        raise ValueError(f"Access to protected path is forbidden: {rel_norm}")

    if for_write and any(
        rel_norm.startswith(prefix) for prefix in STARTER_EXCLUSION_PREFIXES
    ):
        raise ValueError(
            f"Writing inside excluded starter boundary is forbidden: {rel_norm}"
        )

    return requested


def read_repo_file_tool(relative_path: str) -> str:
    """Read a UTF-8 file from the repository while enforcing path and secret guardrails."""
    target = _validate_repo_path(relative_path, for_write=False)
    if not target.is_file():
        raise FileNotFoundError(relative_path)
    return target.read_text(encoding="utf-8")[:6000]


def write_repo_file_tool(relative_path: str, content: str) -> str:
    """Write a UTF-8 file inside the repository while respecting secret and starter boundaries."""
    target = _validate_repo_path(relative_path, for_write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return _normalize_rel_path(target)


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


def _parse_result(
    text: str,
    request: DevArchitectRequest,
    role_meta: RoleMetadata,
) -> DevArchitectResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]

    try:
        payload = json.loads(cleaned)
        payload["task_id"] = request.task_id
        payload["role"] = request.assigned_role
        payload["agent"] = role_meta.agent_id
        if payload.get("status") not in ("completed", "needs_review", "error"):
            payload["status"] = "completed"
        elif payload.get("status") == "needs_review" and (
            payload.get("decisions_or_contracts") or payload.get("proposed_changes")
        ):
            payload["status"] = "completed"
        payload.setdefault(
            "summary",
            f"Completed {request.assigned_role} specification and review for {request.task_id}.",
        )
        payload["human_approval_required"] = True
        return DevArchitectResult.model_validate(payload)
    except (json.JSONDecodeError, ValidationError):
        return DevArchitectResult(
            task_id=request.task_id,
            role=request.assigned_role,
            agent=role_meta.agent_id,
            status="needs_review",
            summary=(
                text[:800].strip()
                or f"{role_meta.agent_id} output could not be parsed as valid JSON; human review required."
            ),
            decisions_or_contracts=[
                "LLM output was unparseable JSON; verify design/implementation manually."
            ],
            proposed_changes=[],
            human_approval_required=role_meta.human_approval_required,
        )


def _format_artifact_markdown(
    result: DevArchitectResult,
    role_meta: RoleMetadata,
) -> str:
    lines = [
        f"# Artifact: {result.task_id} ({role_meta.title} / {result.agent})",
        "",
        f"- **Role ID:** `{result.role}`",
        f"- **Status:** `{result.status}`",
        f"- **Accountable Human:** `{role_meta.accountable_human}`",
        f"- **Human Approval Required:** `{result.human_approval_required}`",
        "",
        "## Summary",
        result.summary,
        "",
        "## Decisions & Contracts",
    ]
    if result.decisions_or_contracts:
        for item in result.decisions_or_contracts:
            lines.append(f"- {item}")
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Proposed File Changes"])
    if result.proposed_changes:
        for change in result.proposed_changes:
            lines.append(f"### `{change.file_path}` ({change.action})")
            lines.append(change.description)
            if change.code_snippet:
                lines.append("```")
                lines.append(change.code_snippet)
                lines.append("```")
    else:
        lines.append("No file changes proposed.")

    return "\n".join(lines) + "\n"


def _invoke_configured_llm_bounded(
    system_text: str,
    human_text: str,
    timeout_seconds: int,
) -> tuple[str | None, tuple[int | None, int | None], str | None]:
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    def _call() -> tuple[str, tuple[int | None, int | None]]:
        response = get_chat_model(json_mode=True).invoke(
            [SystemMessage(content=system_text), HumanMessage(content=human_text)]
        )
        return _message_text(response), usage_from_message(response)

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_call)
    try:
        text, usage = future.result(timeout=timeout_seconds)
        executor.shutdown(wait=False)
        return text, usage, None
    except FuturesTimeoutError:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        return None, (None, None), "LLM call timed out"
    except Exception as exc:
        executor.shutdown(wait=False)
        return None, (None, None), f"{type(exc).__name__}: {exc}"


def _build_role_prompts(
    request: DevArchitectRequest,
    role_meta: RoleMetadata,
    file_contents: dict[str, str],
) -> tuple[str, str]:
    if request.assigned_role == "software_architect":
        role_focus = (
            "Focus on high-level system design, module boundaries, interface contracts, "
            "data models, and key architectural trade-offs or decisions."
        )
    else:
        role_focus = (
            "Focus on concrete backend service implementation, business logic, "
            "API handlers, error handling, and code changes that integrate cleanly "
            "with the existing codebase conventions."
        )

    system_text = (
        f"You are the {role_meta.title} agent ({role_meta.agent_id}).\n"
        f"Role responsibility: {role_meta.responsibility}.\n"
        f"{role_focus}\n"
        "Infer the tech stack and conventions from the provided repository context files.\n"
        "Return ONLY valid JSON with keys: "
        "status, summary, decisions_or_contracts, proposed_changes, human_approval_required.\n"
        "- status must be 'completed', 'needs_review', or 'error'.\n"
        "- decisions_or_contracts is a list of strings.\n"
        "- proposed_changes is a list of objects with keys: "
        "file_path, action ('create'|'modify'|'delete'), description, code_snippet.\n"
        f"- human_approval_required must be {str(role_meta.human_approval_required).lower()}."
    )

    files_section = "\n\n".join(
        f"--- File: {path} ---\n{content}" for path, content in file_contents.items()
    )
    human_text = (
        f"Task ID: {request.task_id}\n"
        f"Task Type: {request.task_type}\n"
        f"Assigned Role: {request.assigned_role} ({role_meta.title})\n"
        f"Description: {request.description}\n\n"
        f"Repository Context:\n{files_section or 'No input files provided.'}"
    )
    return system_text, human_text


def build_graph(llm: Any | None = None):
    def inspect_files(state: DevArchitectState) -> DevArchitectState:
        request = state["request"]
        loaded: dict[str, str] = {}
        tools_used = list(state.get("tools_used", []))
        try:
            for rel_path in request.input_files:
                loaded[rel_path] = read_repo_file_tool(rel_path)
            if request.input_files and "read_repo_file_tool" not in tools_used:
                tools_used.append("read_repo_file_tool")
            return {"file_contents": loaded, "tools_used": tools_used}
        except Exception as exc:
            if "read_repo_file_tool" not in tools_used:
                tools_used.append("read_repo_file_tool")
            return {"error": f"{type(exc).__name__}: {exc}", "tools_used": tools_used}

    def route_after_inspect(state: DevArchitectState):
        return END if state.get("error") else "generate_solution"

    def generate_solution(state: DevArchitectState) -> DevArchitectState:
        request = state["request"]
        role_meta = state["role_meta"]
        system_text, human_text = _build_role_prompts(
            request, role_meta, state.get("file_contents", {})
        )

        if llm is None:
            text, usage, llm_error = _invoke_configured_llm_bounded(
                system_text,
                human_text,
                request.timeout_seconds,
            )
            if llm_error:
                result = DevArchitectResult(
                    task_id=request.task_id,
                    role=request.assigned_role,
                    agent=role_meta.agent_id,
                    status="needs_review",
                    summary=f"Repository files inspected, but LLM generation failed: {llm_error}",
                    decisions_or_contracts=[
                        "Human review required because LLM generation timed out or failed."
                    ],
                    proposed_changes=[],
                    human_approval_required=role_meta.human_approval_required,
                )
                result_dict = result.model_dump()
                result_dict["_usage"] = usage
                return {"result": result_dict}

            result = _parse_result(text or "", request, role_meta)
            result_dict = result.model_dump()
            result_dict["_usage"] = usage
            return {"result": result_dict}

        try:
            response = llm.invoke(
                [SystemMessage(content=system_text), HumanMessage(content=human_text)]
            )
            result = _parse_result(_message_text(response), request, role_meta)
            result_dict = result.model_dump()
            result_dict["_usage"] = usage_from_message(response)
            return {"result": result_dict}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def route_after_generate(state: DevArchitectState):
        if state.get("error"):
            return END
        request = state["request"]
        return "write_artifact" if request.output_artifact_path else END

    def write_artifact(state: DevArchitectState) -> DevArchitectState:
        request = state["request"]
        role_meta = state["role_meta"]
        tools_used = list(state.get("tools_used", []))
        if "write_repo_file_tool" not in tools_used:
            tools_used.append("write_repo_file_tool")

        raw = dict(state["result"])
        usage = raw.pop("_usage", (None, None))
        result = DevArchitectResult.model_validate(raw)

        try:
            assert request.output_artifact_path is not None
            if request.output_artifact_path.endswith(".json"):
                content = result.model_dump_json(indent=2)
            else:
                content = _format_artifact_markdown(result, role_meta)
            written_path = write_repo_file_tool(request.output_artifact_path, content)
            result.written_artifact_path = written_path
            updated = result.model_dump()
            updated["_usage"] = usage
            return {"result": updated, "tools_used": tools_used}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}", "tools_used": tools_used}

    builder = StateGraph(DevArchitectState)
    builder.add_node("inspect_files", inspect_files)
    builder.add_node("generate_solution", generate_solution)
    builder.add_node("write_artifact", write_artifact)

    builder.add_edge(START, "inspect_files")
    builder.add_conditional_edges(
        "inspect_files", route_after_inspect, ["generate_solution", END]
    )
    builder.add_conditional_edges(
        "generate_solution", route_after_generate, ["write_artifact", END]
    )
    builder.add_edge("write_artifact", END)
    return builder.compile()


def run_dev_architect_agent(
    request: DevArchitectRequest,
    *,
    llm: Any | None = None,
    trace_file: str | None = DEFAULT_TRACE_FILE,
) -> DevArchitectResult:
    run_id = str(uuid.uuid4())
    settings = get_settings()
    role_meta = load_role_metadata(request.assigned_role)

    started = time.perf_counter()
    graph = build_graph(llm)
    state = graph.invoke(
        {"request": request, "role_meta": role_meta, "tools_used": []}
    )
    duration = time.perf_counter() - started
    tools_used = state.get("tools_used") or ["read_repo_file_tool"]

    if state.get("error"):
        result = DevArchitectResult(
            task_id=request.task_id,
            role=request.assigned_role,
            agent=role_meta.agent_id,
            status="error",
            summary=state["error"],
            human_approval_required=role_meta.human_approval_required,
        )
        append_trace(
            {
                "run_id": run_id,
                "task_id": request.task_id,
                "agent": role_meta.agent_id,
                "role": request.assigned_role,
                "accountable_human": role_meta.accountable_human,
                "model": settings.llm_model,
                "status": result.status,
                "tools": tools_used,
                "duration_seconds": round(duration, 4),
                "error": state["error"],
            },
            trace_file,
        )
        return result

    raw = dict(state["result"])
    input_tokens, output_tokens = raw.pop("_usage", (None, None))
    result = DevArchitectResult.model_validate(raw)

    append_trace(
        {
            "run_id": run_id,
            "task_id": request.task_id,
            "agent": role_meta.agent_id,
            "role": request.assigned_role,
            "accountable_human": role_meta.accountable_human,
            "model": settings.llm_model,
            "status": result.status,
            "tools": tools_used,
            "written_artifact_path": result.written_artifact_path,
            "duration_seconds": round(duration, 4),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_credits": estimate_cost_credits(
                duration_seconds=duration,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        },
        trace_file,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Developer & Architect Agent (supports software_architect and backend_api_engineer)."
    )
    parser.add_argument("--task-id", default="SESSION-02-DEV-001")
    parser.add_argument(
        "--role",
        choices=["software_architect", "backend_api_engineer"],
        default="backend_api_engineer",
    )
    parser.add_argument(
        "--description",
        required=False,
        default="Analyze the repository context and propose an implementation or architecture design.",
    )
    parser.add_argument(
        "--input-files",
        nargs="*",
        default=["src/app/main.py", "src/app/db.py"],
    )
    parser.add_argument("--output-artifact", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()

    result = run_dev_architect_agent(
        DevArchitectRequest(
            task_id=args.task_id,
            description=args.description,
            assigned_role=args.role,
            input_files=args.input_files,
            output_artifact_path=args.output_artifact,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
