"""Deterministic, read-only security checks on explicitly selected Python files.

This is a focused heuristic check, not a sandbox or a full security audit.
"""
from __future__ import annotations

import ast
import hashlib
import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.agents.quality_support import REPO_ROOT, source_version
from src.models.tasks import EngineeringTask
from src.observability.tracing import append_trace, estimate_cost_credits


class SecurityFinding(BaseModel):
    rule: str
    path: str
    line: int | None = None
    severity: Literal["medium", "high"]
    description: str


class SecurityResult(BaseModel):
    status: Literal["passed", "needs_review", "error"]
    checks: list[str] = Field(default_factory=lambda: [
        "artifact_path_boundary", "dynamic_code_execution", "shell_execution",
        "literal_credentials", "human_approval_policy",
    ])
    findings: list[SecurityFinding] = Field(default_factory=list)
    artifact_sha256: dict[str, str] = Field(default_factory=dict)
    human_approval_required: Literal[True] = True
    run_id: str | None = None
    trace_path: str | None = None


def _artifact_path(relative: str) -> Path:
    path = (REPO_ROOT / relative).resolve()
    try:
        parts = path.relative_to(REPO_ROOT).parts
    except ValueError as exc:
        raise ValueError("Artifact escapes repository") from exc
    if not parts or parts[0] not in {"src", "tests"} or path.suffix != ".py":
        raise ValueError("Only Python files below src/ or tests/ may be inspected")
    if not path.is_file():
        raise FileNotFoundError("Artifact does not exist")
    if path.stat().st_size > 256_000:
        raise ValueError("Artifact exceeds 256 KB limit")
    return path


def inspect_python(relative: str) -> tuple[list[SecurityFinding], str]:
    path = _artifact_path(relative)
    content = path.read_bytes()
    tree = ast.parse(content, filename=relative)
    findings: list[SecurityFinding] = []

    def add(node: ast.AST, rule: str, description: str) -> None:
        findings.append(SecurityFinding(rule=rule, path=relative, line=getattr(node, "lineno", None),
                                        severity="high", description=description))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                add(node, "dynamic_code_execution", "Dynamic Python execution requires human inspection.")
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "os" and node.func.attr in {"system", "popen"}:
                    add(node, "shell_execution", "Shell command execution requires human inspection.")
            if any(keyword.arg == "shell" and isinstance(keyword.value, ast.Constant)
                   and keyword.value.value is True for keyword in node.keywords):
                add(node, "shell_execution", "shell=True requires human inspection.")
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [target.id.lower() for target in targets if isinstance(target, ast.Name)]
            value = node.value
            if (any(any(word in name for word in ("password", "secret", "api_key", "access_token"))
                    for name in names)
                    and isinstance(value, ast.Constant) and isinstance(value.value, str)
                    and len(value.value) >= 8):
                add(node, "literal_credentials", "Possible credential literal; value omitted from report.")
    return findings, hashlib.sha256(content).hexdigest()


def run_security_agent(task: EngineeringTask, *,
                       trace_file: str | None = None, qa_result: dict | None = None) -> SecurityResult:
    task = EngineeringTask.model_validate(task)
    artifacts = task.input_files
    started = time.perf_counter()
    run_id = str(uuid.uuid4())
    result = SecurityResult(status="passed", run_id=run_id)
    tools: list[str] = []
    if qa_result is not None:
        result.checks.append("technical_status_integrity")
        if qa_result.get("human_approval_required") is not True:
            result.findings.append(SecurityFinding(rule="human_approval_policy", path="",
                severity="high", description="Upstream QA result must require human approval."))
        if qa_result.get("status") == "passed" and qa_result.get("pytest_exit_code") != 0:
            result.findings.append(SecurityFinding(rule="technical_status_integrity", path="",
                severity="high", description="QA success contradicts the technical exit code."))
    if not artifacts:
        result.status = "needs_review"
        result.findings.append(SecurityFinding(rule="artifact_scope", path="", severity="medium",
                                                description="No source artifacts selected for inspection."))
    for relative in artifacts:
        try:
            # Validate before claiming the file inspection tool was used.
            _artifact_path(relative)
            tools.append("inspect_python")
            findings, digest = inspect_python(relative)
            result.findings.extend(findings)
            result.artifact_sha256[relative] = digest
        except (OSError, ValueError, SyntaxError) as exc:
            result.status = "error"
            result.findings.append(SecurityFinding(rule="artifact_validation", path=relative,
                severity="high", description=f"Inspection failed ({type(exc).__name__}); contents omitted."))
    if result.findings and result.status != "error":
        result.status = "needs_review"
    duration = time.perf_counter() - started
    path = append_trace({
        "run_id": run_id, "workflow_id": task.workflow_id, "task_id": task.task_id,
        "task": task.model_dump(mode="json"),
        "agent": "quality-security-checker", "role": "ai_safety_security_engineer",
        "upstream_qa_run_id": qa_result.get("run_id") if qa_result else None,
        "provider": "deterministic", "model": None, "calls": 0, "tools": tools,
        "status": result.status, "duration_seconds": round(duration, 4), **source_version(),
        "input_tokens": None, "output_tokens": None,
        "estimated_cost_credits": estimate_cost_credits(
            duration_seconds=duration, input_tokens=None, output_tokens=None, calls=0),
        "result": result.model_dump(exclude={"trace_path"}),
    }, trace_file)
    result.trace_path = str(path)
    return result
