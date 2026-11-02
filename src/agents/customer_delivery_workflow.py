"""Session 3–5 Customer Delivery Workflow:
Multi-agent cooperation (Architect -> Implementation -> QA) on an external product checkout
with workspace sandboxing, strict LLM output validation (no silent default HTML fallback),
bounded correction loops, run manifests with verified Factory commits, and a human review gate.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from src.agents.dev_architect_agent import load_role_metadata
from src.agents.qa_test_agent import QAFinding, QATestResult
from src.agents.quality_support import redact
from src.agents.task_models import (
    CustomerDeliveryTask,
    ProductHandoverPayload,
    QAHandoverPayload,
)
from src.app.settings import get_settings
from src.llm.factory import get_chat_model
from src.observability.tracing import (
    append_trace,
    estimate_cost_credits,
    usage_from_message,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_CONFIG_DIR = REPO_ROOT / "config" / "projects"

AutomatedGateStatus = Literal[
    "pending_approval", "changes_requested", "escalate_to_human"
]

DEFAULT_S3_REQUIRED_CONTENT: dict[str, str] = {
    "N-01": "Nordwerk Industrie-Service",
    "N-02": "Praktische Unterstützung für Ihren technischen Betrieb.",
    "N-03_title": "Wartungsplanung",
    "N-03_text": (
        "Wir strukturieren Wartungsaufgaben und dokumentieren "
        "Zuständigkeiten für kleine technische Betriebe."
    ),
    "N-08_label": "Anfrage stellen",
    "N-08_href": "mailto:kontakt@nordwerk.example",
    "N-09": (
        "Fiktives Unternehmen – Lehrprojekt der HAW Hamburg. "
        "Keine realen Angebote oder Kontaktaufnahme."
    ),
}

DEFAULT_S4_REQUIRED_CONTENT: dict[str, str] = {
    "N-01": "Nordwerk Industrie-Service",
    "N-02": "Praktische Unterstützung für Ihren technischen Betrieb.",
    "N-03_title": "Wartungsplanung",
    "N-03_text": (
        "Wir strukturieren Wartungsaufgaben und dokumentieren "
        "Zuständigkeiten für kleine technische Betriebe."
    ),
    "N-04_title": "Ersatzteilkoordination",
    "N-04_text": (
        "Wir unterstützen bei der Abstimmung von Ersatzteilbedarfen "
        "und Lieferterminen."
    ),
    "N-05_title": "Betriebsdokumentation",
    "N-05_text": (
        "Wir bringen technische Unterlagen in eine nachvollziehbare "
        "und nutzbare Struktur."
    ),
    "N-06_target_1": "Kleine Produktionsbetriebe",
    "N-06_target_2": "Technische Serviceunternehmen",
    "N-07": (
        "Ein fester Ansprechpartner, ein gemeinsam vereinbarter "
        "Leistungsumfang und nachvollziehbare Ergebnisse."
    ),
    "N-08_label": "Anfrage stellen",
    "N-08_href": "mailto:kontakt@nordwerk.example",
    "N-09": (
        "Fiktives Unternehmen – Lehrprojekt der HAW Hamburg. "
        "Keine realen Angebote oder Kontaktaufnahme."
    ),
}

DEFAULT_REQUIRED_CONTENT: dict[str, str] = dict(DEFAULT_S4_REQUIRED_CONTENT)


class ArchitectPlanResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    agent: str
    role: str = "software_architect"
    accountable_human: str
    status: Literal["completed", "needs_review", "error"]
    summary: str
    handover: ProductHandoverPayload
    tools_used: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_credits: float = 0.0


class ImplementationStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    iteration: int
    agent: str
    role: str = "backend_api_engineer"
    accountable_human: str
    status: Literal["completed", "needs_review", "error"]
    summary: str
    written_file: str | None = None
    artifact_sha256: str = ""
    patch_path: str | None = None
    handover: QAHandoverPayload
    tools_used: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_credits: float = 0.0


class CustomerDeliveryWorkflowResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    project_id: str
    task_id: str
    product_repo_path: str
    factory_commit: str
    factory_code_clean: bool = True
    product_input_commit: str
    product_output_commit: str
    iterations_used: int
    max_correction_loops: int
    architect_result: ArchitectPlanResult
    implementation_history: list[ImplementationStepResult] = Field(default_factory=list)
    qa_history: list[QATestResult] = Field(default_factory=list)
    final_qa_result: QATestResult | None = None
    run_directory: str
    trace_file: str
    manifest_file: str
    patch_file: str | None = None
    human_gate_status: AutomatedGateStatus = "pending_approval"
    human_approval_required: Literal[True] = True
    approved_by_human: None = None
    total_estimated_agent_credits: float = 0.0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CustomerHumanReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    project_id: str
    workflow_id: str
    decision: Literal["approved", "changes_requested", "escalate_to_human"]
    reviewer: str = Field(min_length=2, max_length=120)
    decided_at_utc: str
    tested_source_commit: str
    product_input_commit: str
    reviewed_artifact_hashes: dict[str, str]
    report_path: str
    report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    test_evidence_paths: list[str] = Field(default_factory=list)
    accepted_criteria: list[str] = Field(default_factory=list)
    open_criteria: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=3)
    identity_assurance: str = "self_declared_course_review"


class DeliveryWorkflowState(TypedDict, total=False):
    task: CustomerDeliveryTask
    required_content: dict[str, str]
    run_dir: Path
    trace_file: str
    initial_file_snapshot: str
    architect_result: ArchitectPlanResult
    product_handover: ProductHandoverPayload
    qa_handover: QAHandoverPayload
    implementation_history: list[ImplementationStepResult]
    qa_history: list[QATestResult]
    qa_feedback: str
    iteration: int
    human_gate_status: AutomatedGateStatus


def load_project_config(
    project_id: str = "website-01",
    config_dir: Path = PROJECTS_CONFIG_DIR,
) -> dict[str, Any]:
    """Load project configuration YAML from config/projects/<project_id>.yaml."""
    config_path = config_dir / f"{project_id}.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"Project configuration not found: {config_path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid project configuration in {config_path}")
    return data


def build_task_from_project_config(
    project_id: str = "website-01",
    *,
    product_repo_path: str | None = None,
    task_id: str | None = None,
    workflow_id: str | None = None,
    max_correction_loops: int | None = None,
    config_dir: Path = PROJECTS_CONFIG_DIR,
) -> tuple[CustomerDeliveryTask, dict[str, str]]:
    """Construct a CustomerDeliveryTask and required_content dictionary from project config."""
    cfg = load_project_config(project_id, config_dir=config_dir)
    effective_task_id = task_id or str(cfg.get("customer_task_id", "NW-S4-001"))

    tasks_map = cfg.get("tasks") if isinstance(cfg.get("tasks"), dict) else {}
    task_cfg = (
        tasks_map.get(effective_task_id)
        if isinstance(tasks_map, dict) and isinstance(tasks_map.get(effective_task_id), dict)
        else {}
    )

    if effective_task_id.startswith("NW-S3"):
        req_content = dict(DEFAULT_S3_REQUIRED_CONTENT)
    else:
        req_content = dict(DEFAULT_S4_REQUIRED_CONTENT)
        if isinstance(cfg.get("required_content"), dict):
            req_content.update(
                {str(k): str(v) for k, v in cfg["required_content"].items()}
            )

    if isinstance(task_cfg.get("required_content"), dict):
        req_content = {
            str(k): str(v) for k, v in task_cfg["required_content"].items()
        }

    input_files = list(
        task_cfg.get(
            "product_input_files",
            cfg.get(
                "product_input_files",
                ["docs/issue-02-session-04.md", "site/index.html", "site/styles.css"],
            ),
        )
    )
    test_target = str(
        task_cfg.get(
            "product_test_target",
            cfg.get("product_test_target", "tests/test_website_s4.py"),
        )
    )
    ac_list = list(
        task_cfg.get(
            "acceptance_criteria_in_scope",
            cfg.get(
                "acceptance_criteria_in_scope",
                ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05", "AC-06", "AC-07", "AC-08"],
            ),
        )
    )
    description = str(
        task_cfg.get(
            "description",
            cfg.get(
                "description",
                f"Deliver customer task {effective_task_id} for {project_id}.",
            ),
        )
    )

    task = CustomerDeliveryTask(
        task_id=effective_task_id,
        workflow_id=workflow_id or f"WF-{project_id.upper()}-{uuid.uuid4().hex[:8]}",
        description=description,
        project_id=str(cfg.get("project_id", project_id)),
        product_repo_path=product_repo_path
        or str(cfg.get("product_repo_path", "../client-01-website")),
        input_files=input_files,
        target_product_file=str(cfg.get("target_product_file", "site/index.html")),
        product_test_target=test_target,
        allowed_write_prefixes=list(cfg.get("allowed_write_prefixes", ["site/"])),
        acceptance_criteria=[str(x) for x in ac_list],
        required_content=dict(req_content),
        max_correction_loops=max_correction_loops
        if max_correction_loops is not None
        else int(cfg.get("max_correction_loops", 2)),
    )
    return task, req_content


def resolve_product_repo_root(product_repo_path: str | Path) -> Path:
    """Resolve the external customer product repository path."""
    raw = Path(product_repo_path)
    resolved = raw.resolve() if raw.is_absolute() else (REPO_ROOT / raw).resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(
            f"Configured product repository directory does not exist: {resolved}"
        )
    return resolved


def validate_product_workspace_path(
    product_repo_path: str | Path,
    relative_path: str,
    *,
    for_write: bool = False,
    allowed_write_prefixes: list[str] | None = None,
) -> Path:
    """Enforce strict sandbox boundaries on the customer product workspace (Criterion A4)."""
    if not relative_path or not relative_path.strip():
        raise ValueError("Product file path must not be empty")

    product_root = resolve_product_repo_root(product_repo_path)
    requested = (product_root / relative_path).resolve()
    try:
        rel_to_product = requested.relative_to(product_root)
    except ValueError as exc:
        raise ValueError(
            f"Path escapes configured product workspace ({product_root}): {relative_path}"
        ) from exc

    rel_norm = str(rel_to_product).replace("\\", "/")
    parts = rel_norm.split("/")

    # Never allow access to secrets (.env*) or VCS internals (.git)
    if (
        requested.name.startswith(".env")
        or ".git" in parts
        or rel_norm.startswith(".git/")
    ):
        raise ValueError(
            f"Access to protected path in product workspace is forbidden: {rel_norm}"
        )

    if for_write:
        prefixes = allowed_write_prefixes if allowed_write_prefixes is not None else ["site/"]
        normalized_prefixes = [
            p.replace("\\", "/").lstrip("/") for p in prefixes if p.strip()
        ]
        if not any(rel_norm.startswith(prefix) for prefix in normalized_prefixes):
            raise ValueError(
                f"Writing outside allowed product directories {normalized_prefixes} "
                f"is forbidden: {rel_norm}"
            )

    return requested


def read_product_file_tool(
    product_repo_path: str | Path,
    relative_path: str,
) -> str:
    """Read a UTF-8 file inside the customer product checkout."""
    target = validate_product_workspace_path(
        product_repo_path, relative_path, for_write=False
    )
    if not target.is_file():
        raise FileNotFoundError(f"Product file not found: {relative_path}")
    return target.read_text(encoding="utf-8")[:8000]


def write_product_file_tool(
    product_repo_path: str | Path,
    relative_path: str,
    content: str,
    *,
    allowed_write_prefixes: list[str] | None = None,
) -> tuple[str, str]:
    """Write a UTF-8 file inside the allowed area of the customer product checkout.

    Returns (normalized_relative_path, sha256_hex).
    """
    target = validate_product_workspace_path(
        product_repo_path,
        relative_path,
        for_write=True,
        allowed_write_prefixes=allowed_write_prefixes,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    raw_bytes = target.read_bytes()
    product_root = resolve_product_repo_root(product_repo_path)
    rel_norm = str(target.relative_to(product_root)).replace("\\", "/")
    return rel_norm, hashlib.sha256(raw_bytes).hexdigest()


def run_product_test_tool(
    product_repo_path: str | Path,
    product_test_target: str,
    timeout_seconds: int = 60,
) -> tuple[int, str]:
    """Execute the automated product test inside the customer product repository."""
    product_root = resolve_product_repo_root(product_repo_path)
    target = validate_product_workspace_path(
        product_root, product_test_target, for_write=False
    )
    if not target.is_file():
        raise FileNotFoundError(f"Product test file not found: {product_test_target}")

    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", str(target), "-q"],
        cwd=product_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)
        raise

    output = "\n".join(
        part.strip() for part in (stdout, stderr) if part and part.strip()
    )
    return process.returncode, redact(output)[-6000:]


def _git_head_commit(repo_dir: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _git_code_worktree_clean(repo_dir: Path) -> bool:
    """Verify whether Factory code & config (src/ and config/) are committed cleanly in HEAD."""
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "config"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode == 0:
            return len(completed.stdout.strip()) == 0
    except Exception:
        pass
    return False


def _ollama_model_digest(model_name: str) -> str:
    try:
        completed = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode == 0:
            for line in completed.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0] == model_name:
                    return f"{parts[0]}@{parts[1]}"
    except Exception:
        pass
    return model_name


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


def _extract_json_dict(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")
    return parsed


def _invoke_llm(
    llm: Any | None,
    system_text: str,
    human_text: str,
    *,
    max_output_tokens: int | None = None,
) -> tuple[str | None, tuple[int | None, int | None], str | None]:
    try:
        model = (
            llm
            if llm is not None
            else get_chat_model(
                reasoning=False,
                json_mode=True,
                max_output_tokens=max_output_tokens,
            )
        )
        response = model.invoke(
            [SystemMessage(content=system_text), HumanMessage(content=human_text)]
        )
        return _message_text(response), usage_from_message(response), None
    except Exception as exc:
        return None, (None, None), f"{type(exc).__name__}: {exc}"


def _non_empty_str(mapping: dict[str, Any], key: str) -> str:
    val = mapping.get(key)
    if not isinstance(val, str) or not val.strip():
        raise ValueError(f"Missing or empty required LLM field: '{key}'")
    return val.strip()


def _render_html_document(
    fields: dict[str, Any],
    *,
    required_content: dict[str, str] | None = None,
) -> str:
    """Validate structured LLM output fields and render semantic German HTML5.

    Session 3 feedback remediation:
    Never fall back to DEFAULT_REQUIRED_CONTENT when the LLM fails, times out,
    returns invalid JSON, or omits required content fields. Any missing required
    field raises a ValueError so the workflow records an error and blocks approval.
    """
    if not isinstance(fields, dict) or not fields:
        raise ValueError("LLM output is empty or not a JSON object")

    if isinstance(fields.get("html_content"), str) and fields["html_content"].strip():
        return fields["html_content"].strip()

    # Unwrap nested content dictionary if the LLM placed keys under 'required_content' or 'content'
    candidate_map: dict[str, Any] = dict(fields)
    for nested_key in ("required_content", "content"):
        nested = fields.get(nested_key)
        if isinstance(nested, dict):
            for k, v in nested.items():
                candidate_map.setdefault(str(k), v)

    expected_req = required_content or {}
    is_s4_scope = "N-04_title" in expected_req or "N-04_title" in candidate_map

    # Case 1: Content-ID keyed JSON response (N-01..N-09, plus optional R-01)
    if "N-01" in candidate_map:
        keys_to_verify = (
            list(expected_req.keys())
            if expected_req
            else (
                list(DEFAULT_S4_REQUIRED_CONTENT.keys())
                if is_s4_scope
                else list(DEFAULT_S3_REQUIRED_CONTENT.keys())
            )
        )
        missing = [
            k
            for k in keys_to_verify
            if not isinstance(candidate_map.get(k), str)
            or not str(candidate_map.get(k)).strip()
        ]
        if missing:
            raise ValueError(
                f"LLM JSON output missing required content keys: {missing}"
            )

        company_name = _non_empty_str(candidate_map, "N-01")
        main_statement = _non_empty_str(candidate_map, "N-02")
        contact_label = _non_empty_str(candidate_map, "N-08_label")
        contact_href = _non_empty_str(candidate_map, "N-08_href")
        course_notice = _non_empty_str(candidate_map, "N-09")

        if not is_s4_scope and "N-04_title" not in candidate_map:
            s1_title = _non_empty_str(candidate_map, "N-03_title")
            s1_text = _non_empty_str(candidate_map, "N-03_text")
            return _format_s3_html(
                company_name=company_name,
                main_statement=main_statement,
                service_title=s1_title,
                service_description=s1_text,
                contact_label=contact_label,
                contact_href=contact_href,
                course_notice=course_notice,
            )

        services: list[tuple[str, str]] = [
            (
                _non_empty_str(candidate_map, "N-03_title"),
                _non_empty_str(candidate_map, "N-03_text"),
            ),
            (
                _non_empty_str(candidate_map, "N-04_title"),
                _non_empty_str(candidate_map, "N-04_text"),
            ),
            (
                _non_empty_str(candidate_map, "N-05_title"),
                _non_empty_str(candidate_map, "N-05_text"),
            ),
        ]
        if "R-01_title" in keys_to_verify or "R-01_title" in candidate_map:
            services.append(
                (
                    _non_empty_str(candidate_map, "R-01_title"),
                    _non_empty_str(candidate_map, "R-01_text"),
                )
            )

        target_groups = [
            _non_empty_str(candidate_map, "N-06_target_1"),
            _non_empty_str(candidate_map, "N-06_target_2"),
        ]
        working_approach = _non_empty_str(candidate_map, "N-07")
        nav_leistungen_href = str(
            candidate_map.get("nav_leistungen_href") or "#leistungen"
        ).strip()
        nav_zielgruppen_href = str(
            candidate_map.get("nav_zielgruppen_href") or "#zielgruppen"
        ).strip()
        nav_arbeitsweise_href = str(
            candidate_map.get("nav_arbeitsweise_href") or "#arbeitsweise"
        ).strip()
        nav_kontakt_href = str(
            candidate_map.get("nav_kontakt_href") or "#kontakt"
        ).strip()

        return _format_s4_html(
            company_name=company_name,
            main_statement=main_statement,
            services=services,
            target_groups=target_groups,
            working_approach=working_approach,
            contact_label=contact_label,
            contact_href=contact_href,
            course_notice=course_notice,
            nav_links=[
                (nav_leistungen_href, "Leistungen"),
                (nav_zielgruppen_href, "Zielgruppen"),
                (nav_arbeitsweise_href, "Arbeitsweise"),
                (nav_kontakt_href, "Kontakt"),
            ],
        )

    # Case 2: Session 4 structured field schema ('services', 'target_groups', 'working_approach')
    if "services" in candidate_map or is_s4_scope:
        if is_s4_scope and "services" not in candidate_map:
            raise ValueError(
                "LLM JSON output missing required Session 4 keys ('N-01'..'N-09' or 'services')"
            )
        company_name = _non_empty_str(candidate_map, "company_name")
        main_statement = _non_empty_str(candidate_map, "main_statement")
        contact_label = _non_empty_str(candidate_map, "contact_label")
        contact_href = _non_empty_str(candidate_map, "contact_href")
        course_notice = _non_empty_str(candidate_map, "course_notice")
        working_approach = _non_empty_str(candidate_map, "working_approach")

        raw_services = candidate_map.get("services")
        if not isinstance(raw_services, list) or len(raw_services) < 3:
            raise ValueError(
                "LLM JSON field 'services' must be a list of at least 3 service objects"
            )
        parsed_services: list[tuple[str, str]] = []
        for idx, item in enumerate(raw_services):
            if not isinstance(item, dict):
                raise ValueError(f"Service item at index {idx} is not an object")
            s_title = str(item.get("title") or "").strip()
            s_text = str(item.get("text") or item.get("description") or "").strip()
            if not s_title or not s_text:
                raise ValueError(f"Service item at index {idx} missing title or text")
            parsed_services.append((s_title, s_text))

        raw_targets = candidate_map.get("target_groups")
        if not isinstance(raw_targets, list) or len(raw_targets) < 2:
            raise ValueError(
                "LLM JSON field 'target_groups' must contain at least 2 target groups"
            )
        parsed_targets = [str(t).strip() for t in raw_targets if str(t).strip()]
        if len(parsed_targets) < 2:
            raise ValueError("LLM JSON field 'target_groups' contains empty entries")

        return _format_s4_html(
            company_name=company_name,
            main_statement=main_statement,
            services=parsed_services,
            target_groups=parsed_targets,
            working_approach=working_approach,
            contact_label=contact_label,
            contact_href=contact_href,
            course_notice=course_notice,
        )

    # Case 3: Session 3 slice field schema ('company_name', 'service_title', etc.)
    s3_required_keys = [
        "company_name",
        "main_statement",
        "service_title",
        "service_description",
        "contact_label",
        "contact_href",
        "course_notice",
    ]
    missing_s3 = [
        k
        for k in s3_required_keys
        if not isinstance(candidate_map.get(k), str)
        or not str(candidate_map.get(k)).strip()
    ]
    if missing_s3:
        raise ValueError(
            f"LLM JSON output missing required Session 3 fields: {missing_s3}"
        )

    return _format_s3_html(
        company_name=_non_empty_str(candidate_map, "company_name"),
        main_statement=_non_empty_str(candidate_map, "main_statement"),
        service_title=_non_empty_str(candidate_map, "service_title"),
        service_description=_non_empty_str(candidate_map, "service_description"),
        contact_label=_non_empty_str(candidate_map, "contact_label"),
        contact_href=_non_empty_str(candidate_map, "contact_href"),
        course_notice=_non_empty_str(candidate_map, "course_notice"),
    )


def _format_s3_html(
    *,
    company_name: str,
    main_statement: str,
    service_title: str,
    service_description: str,
    contact_label: str,
    contact_href: str,
    course_notice: str,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{company_name} – Technischer Betrieb &amp; Wartungsplanung</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="course-notice" role="note" aria-label="Übungshinweis">
    {course_notice}
  </div>

  <main class="container">
    <header class="hero" id="start">
      <h1>{company_name}</h1>
      <p class="lead">{main_statement}</p>
    </header>

    <section class="services" id="leistungen" aria-labelledby="leistungen-heading">
      <h2 id="leistungen-heading">Unsere Leistung im Überblick</h2>
      <article class="service-card">
        <h3>{service_title}</h3>
        <p>{service_description}</p>
      </article>
    </section>

    <section class="contact" id="kontakt" aria-labelledby="kontakt-heading">
      <h2 id="kontakt-heading">Kontakt</h2>
      <p>Sie möchten unverbindlich Informationen anfordern? Kontaktieren Sie uns direkt per E-Mail:</p>
      <a class="cta-link" href="{contact_href}">{contact_label}</a>
    </section>
  </main>

  <footer>
    <p>&copy; 2026 {company_name} · Hamburg</p>
  </footer>
</body>
</html>
"""


def _format_s4_html(
    *,
    company_name: str,
    main_statement: str,
    services: list[tuple[str, str]],
    target_groups: list[str],
    working_approach: str,
    contact_label: str,
    contact_href: str,
    course_notice: str,
    nav_links: list[tuple[str, str]] | None = None,
) -> str:
    effective_nav = nav_links or [
        ("#leistungen", "Leistungen"),
        ("#zielgruppen", "Zielgruppen"),
        ("#arbeitsweise", "Arbeitsweise"),
        ("#kontakt", "Kontakt"),
    ]
    nav_items_html = "\n".join(
        f'          <li><a href="{href}">{label}</a></li>'
        for href, label in effective_nav
    )
    service_cards_html = "\n".join(
        f"""        <article class="service-card">
          <h3>{title}</h3>
          <p>{text}</p>
        </article>"""
        for title, text in services
    )
    target_items_html = "\n".join(
        f'        <li class="target-item">{group}</li>'
        for group in target_groups
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{company_name} – Technischer Betrieb &amp; Industrieservice</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="course-notice" role="note" aria-label="Übungshinweis">
    {course_notice}
  </div>

  <header class="site-header">
    <div class="container header-inner">
      <a class="brand-link" href="#start">{company_name}</a>
      <nav class="site-nav" aria-label="Hauptnavigation">
        <ul class="nav-list">
{nav_items_html}
        </ul>
      </nav>
    </div>
  </header>

  <main class="container">
    <section class="hero" id="start" aria-labelledby="hero-heading">
      <h1 id="hero-heading">{company_name}</h1>
      <p class="lead">{main_statement}</p>
      <p class="hero-actions">
        <a class="cta-link" href="{contact_href}">{contact_label}</a>
      </p>
    </section>

    <section class="services" id="leistungen" aria-labelledby="leistungen-heading">
      <h2 id="leistungen-heading">Unsere Leistungen</h2>
      <div class="services-grid">
{service_cards_html}
      </div>
    </section>

    <section class="target-groups" id="zielgruppen" aria-labelledby="zielgruppen-heading">
      <h2 id="zielgruppen-heading">Zielgruppen</h2>
      <p>Unsere Unterstützung richtet sich insbesondere an:</p>
      <ul class="target-list">
{target_items_html}
      </ul>
    </section>

    <section class="working-approach" id="arbeitsweise" aria-labelledby="arbeitsweise-heading">
      <h2 id="arbeitsweise-heading">Unsere Arbeitsweise</h2>
      <p>{working_approach}</p>
    </section>

    <section class="contact" id="kontakt" aria-labelledby="kontakt-heading">
      <h2 id="kontakt-heading">Kontakt</h2>
      <p>Sie möchten unverbindlich Informationen anfordern? Kontaktieren Sie uns direkt per E-Mail:</p>
      <a class="cta-link" href="{contact_href}">{contact_label}</a>
    </section>
  </main>

  <footer>
    <p>&copy; 2026 {company_name} · Hamburg</p>
  </footer>
</body>
</html>
"""


def run_customer_delivery_workflow(
    task: CustomerDeliveryTask | None = None,
    *,
    project_id: str = "website-01",
    architect_llm: Any | None = None,
    implementation_llm: Any | None = None,
    qa_llm: Any | None = None,
    runs_root: Path | None = None,
    fault_overrides: dict[str, str] | None = None,
) -> CustomerDeliveryWorkflowResult:
    """Execute the multi-agent customer delivery workflow on the external product repo."""
    if task is None:
        task, required_content = build_task_from_project_config(project_id=project_id)
    elif task.required_content:
        required_content = dict(task.required_content)
    elif task.task_id.startswith("NW-S3"):
        required_content = dict(DEFAULT_S3_REQUIRED_CONTENT)
    else:
        required_content = dict(DEFAULT_S4_REQUIRED_CONTENT)

    if fault_overrides:
        required_content.update(
            {str(k): str(v) for k, v in fault_overrides.items()}
        )

    settings = get_settings()
    product_root = resolve_product_repo_root(task.product_repo_path)
    factory_commit = _git_head_commit(REPO_ROOT)
    factory_code_clean = _git_code_worktree_clean(REPO_ROOT)
    product_input_commit = _git_head_commit(product_root)

    base_runs_dir = runs_root if runs_root is not None else (REPO_ROOT / "runs")
    run_dir = (base_runs_dir / task.project_id / task.workflow_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    trace_file = str(run_dir / "trace.jsonl")

    initial_snapshot = ""
    try:
        initial_snapshot = read_product_file_tool(
            product_root, task.target_product_file
        )
    except Exception:
        initial_snapshot = ""

    def architect_node(state: DeliveryWorkflowState) -> DeliveryWorkflowState:
        t = state["task"]
        req_map = state["required_content"]
        role_meta = load_role_metadata("software_architect")
        step_run_id = str(uuid.uuid4())
        started = time.perf_counter()
        tools_used: list[str] = []
        loaded_files: dict[str, str] = {}

        for rel_path in t.input_files:
            try:
                loaded_files[rel_path] = read_product_file_tool(product_root, rel_path)
                if "read_product_file_tool" not in tools_used:
                    tools_used.append("read_product_file_tool")
            except FileNotFoundError:
                continue

        first_issue_excerpt = ""
        for rel_path, content in loaded_files.items():
            if rel_path.startswith("docs/"):
                first_issue_excerpt = content[:1500]
                break

        system_text = (
            "You are the Software Architect agent planning customer delivery "
            "for Nordwerk Industrie-Service. Return ONLY valid JSON with keys: "
            "summary (short string < 20 words), architecture_decisions (list of 3 short strings), "
            "and ready_for_implementation (true)."
        )
        human_text = (
            "/no_think\n"
            f"Project ID: {t.project_id}\n"
            f"Task ID: {t.task_id}\n"
            f"Description: {t.description}\n"
            f"Target File: {t.target_product_file}\n"
            f"Required Content Keys: {list(req_map.keys())}\n"
            f"Customer Issue Excerpt:\n{first_issue_excerpt}"
        )
        text, usage, llm_error = _invoke_llm(architect_llm, system_text, human_text)
        duration = time.perf_counter() - started
        in_tok, out_tok = usage
        calls = 0 if llm_error and architect_llm is None else 1
        credits = estimate_cost_credits(
            duration_seconds=duration,
            input_tokens=in_tok,
            output_tokens=out_tok,
            calls=calls,
        )

        decisions: list[str] = []
        summary = ""
        status: Literal["completed", "needs_review", "error"] = "completed"
        ready_flag = True

        if llm_error:
            status = "error"
            ready_flag = False
            summary = f"Architect LLM call failed: {llm_error}"
        elif not text:
            status = "error"
            ready_flag = False
            summary = "Architect LLM returned empty response."
        else:
            try:
                parsed = _extract_json_dict(text)
                if isinstance(parsed.get("summary"), str) and parsed["summary"].strip():
                    summary = parsed["summary"].strip()
                if (
                    isinstance(parsed.get("architecture_decisions"), list)
                    and parsed["architecture_decisions"]
                ):
                    decisions = [str(x) for x in parsed["architecture_decisions"] if str(x).strip()]
                if not summary or not decisions:
                    raise ValueError("Architect JSON missing non-empty 'summary' or 'architecture_decisions'")
            except Exception as exc:
                status = "error"
                ready_flag = False
                summary = f"Architect LLM output invalid JSON ({type(exc).__name__}: {exc})"

        ac_list = (
            list(t.acceptance_criteria)
            if t.acceptance_criteria
            else (
                ["AC-01", "AC-02 (N-03)", "AC-04"]
                if t.task_id.startswith("NW-S3")
                else ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05", "AC-06", "AC-07", "AC-08"]
            )
        )

        handover = ProductHandoverPayload(
            from_agent=role_meta.agent_id,
            from_role="software_architect",
            to_role="backend_api_engineer",
            project_id=t.project_id,
            task_id=t.task_id,
            workflow_id=t.workflow_id,
            product_repo_path=str(product_root),
            target_product_file=t.target_product_file,
            acceptance_criteria=ac_list,
            required_content=req_map,
            architecture_decisions=decisions,
            ready_for_implementation=ready_flag,
        )

        plan_res = ArchitectPlanResult(
            run_id=step_run_id,
            agent=role_meta.agent_id,
            role="software_architect",
            accountable_human=role_meta.accountable_human,
            status=status,
            summary=summary,
            handover=handover,
            tools_used=tools_used,
            duration_seconds=round(duration, 4),
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_credits=credits,
        )

        append_trace(
            {
                "run_id": step_run_id,
                "workflow_id": t.workflow_id,
                "project_id": t.project_id,
                "task_id": t.task_id,
                "agent": role_meta.agent_id,
                "role": "software_architect",
                "accountable_human": role_meta.accountable_human,
                "provider": settings.llm_provider if architect_llm is None else "injected",
                "model": settings.llm_model if architect_llm is None else type(architect_llm).__name__,
                "status": plan_res.status,
                "tools": tools_used,
                "handover_to": handover.to_role,
                "duration_seconds": plan_res.duration_seconds,
                "calls": calls,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "estimated_cost_credits": credits,
            },
            state["trace_file"],
        )
        return {"architect_result": plan_res, "product_handover": handover}

    def implementation_node(state: DeliveryWorkflowState) -> DeliveryWorkflowState:
        t = state["task"]
        handover = state["product_handover"]
        iteration = state.get("iteration", 0) + 1
        feedback = state.get("qa_feedback", "")
        role_meta = load_role_metadata("backend_api_engineer")
        step_run_id = str(uuid.uuid4())
        started = time.perf_counter()

        expected_keys = list(handover.required_content.keys())
        system_text = (
            "You are the Implementation Engineer agent generating the Nordwerk Industrie-Service "
            "website from the Architect's required_content contract. "
            "Return ONLY a single flat JSON object containing:\n"
            "- \"summary\": a short sentence (< 12 words)\n"
            f"- Every key in {json.dumps(expected_keys)} mapped to its exact verbatim German string.\n"
            "Do not omit any key, do not nest keys, and do not modify the German strings."
        )
        human_text = (
            "/no_think\n"
            f"Iteration: {iteration} of {t.max_correction_loops}\n"
            f"Target File: {handover.target_product_file}\n"
            f"Required Content Contract:\n{json.dumps(handover.required_content, ensure_ascii=False, indent=2)}\n"
        )
        if feedback:
            human_text += f"\nPrevious Failure Feedback to Fix:\n{feedback}\n"

        imp_token_limit = max(settings.llm_max_output_tokens, 640)
        text, usage, llm_error = _invoke_llm(
            implementation_llm,
            system_text,
            human_text,
            max_output_tokens=imp_token_limit,
        )
        in_tok, out_tok = usage
        calls = 0 if llm_error and implementation_llm is None else 1

        written_rel: str | None = None
        sha256_hex = ""
        patch_file_str: str | None = None
        tools_used: list[str] = []
        status: Literal["completed", "needs_review", "error"] = "completed"
        ready_for_qa = True
        summary = f"Generated {t.target_product_file} in product checkout (iteration {iteration})."

        if llm_error:
            status = "error"
            ready_for_qa = False
            summary = f"LLM implementation call failed (no fallback HTML written): {llm_error}"
        elif not text:
            status = "error"
            ready_for_qa = False
            summary = "LLM implementation call returned empty output (no fallback HTML written)."
        else:
            try:
                parsed_fields = _extract_json_dict(text)
                if isinstance(parsed_fields.get("summary"), str) and parsed_fields["summary"].strip():
                    summary = parsed_fields["summary"].strip()
                html_content = _render_html_document(
                    parsed_fields,
                    required_content=handover.required_content,
                )
                written_rel, sha256_hex = write_product_file_tool(
                    product_root,
                    t.target_product_file,
                    html_content,
                    allowed_write_prefixes=t.allowed_write_prefixes,
                )
                tools_used = ["write_product_file_tool"]

                diff_lines = list(
                    difflib.unified_diff(
                        state.get("initial_file_snapshot", "").splitlines(keepends=True),
                        html_content.splitlines(keepends=True),
                        fromfile=f"a/{written_rel}",
                        tofile=f"b/{written_rel}",
                    )
                )
                patch_file = state["run_dir"] / "changes.patch"
                patch_file.write_text("".join(diff_lines), encoding="utf-8")
                patch_file_str = str(patch_file)
            except Exception as exc:
                status = "error"
                ready_for_qa = False
                summary = (
                    f"LLM implementation output validation failed "
                    f"(no fallback HTML written): {type(exc).__name__}: {exc}"
                )

        duration = time.perf_counter() - started
        credits = estimate_cost_credits(
            duration_seconds=duration,
            input_tokens=in_tok,
            output_tokens=out_tok,
            calls=calls,
        )

        qa_handover = QAHandoverPayload(
            from_agent=role_meta.agent_id,
            from_role="backend_api_engineer",
            to_role="qa_test_engineer",
            project_id=t.project_id,
            task_id=t.task_id,
            workflow_id=t.workflow_id,
            product_repo_path=str(product_root),
            modified_files=[written_rel] if written_rel else [],
            artifact_sha256=sha256_hex,
            product_test_target=t.product_test_target,
            acceptance_criteria=handover.acceptance_criteria,
            iteration=iteration,
            ready_for_qa=ready_for_qa,
        )

        imp_res = ImplementationStepResult(
            run_id=step_run_id,
            iteration=iteration,
            agent=role_meta.agent_id,
            role="backend_api_engineer",
            accountable_human=role_meta.accountable_human,
            status=status,
            summary=summary,
            written_file=written_rel,
            artifact_sha256=sha256_hex,
            patch_path=patch_file_str,
            handover=qa_handover,
            tools_used=tools_used,
            duration_seconds=round(duration, 4),
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_credits=credits,
        )

        append_trace(
            {
                "run_id": step_run_id,
                "workflow_id": t.workflow_id,
                "project_id": t.project_id,
                "task_id": t.task_id,
                "iteration": iteration,
                "agent": role_meta.agent_id,
                "role": "backend_api_engineer",
                "accountable_human": role_meta.accountable_human,
                "provider": settings.llm_provider if implementation_llm is None else "injected",
                "model": settings.llm_model if implementation_llm is None else type(implementation_llm).__name__,
                "status": imp_res.status,
                "tools": tools_used,
                "written_file": written_rel,
                "artifact_sha256": sha256_hex,
                "handover_to": qa_handover.to_role,
                "duration_seconds": imp_res.duration_seconds,
                "calls": calls,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "estimated_cost_credits": credits,
            },
            state["trace_file"],
        )

        history = list(state.get("implementation_history", []))
        history.append(imp_res)
        return {
            "iteration": iteration,
            "qa_handover": qa_handover,
            "implementation_history": history,
        }

    def product_qa_node(state: DeliveryWorkflowState) -> DeliveryWorkflowState:
        t = state["task"]
        qa_handover = state["qa_handover"]
        latest_imp = state["implementation_history"][-1]
        role_meta = load_role_metadata("qa_test_engineer")
        step_run_id = str(uuid.uuid4())
        started = time.perf_counter()

        exit_code, test_output = run_product_test_tool(
            product_root,
            qa_handover.product_test_target,
            timeout_seconds=t.timeout_seconds,
        )

        imp_succeeded = (
            latest_imp.status == "completed"
            and qa_handover.ready_for_qa
            and bool(latest_imp.written_file)
        )
        tech_status: Literal["passed", "failed", "needs_review", "error"] = (
            "passed" if (exit_code == 0 and imp_succeeded) else "failed"
        )

        system_text = (
            "You are the QA & Test Engineer agent verifying the Nordwerk customer product check. "
            "Return ONLY valid JSON with keys: status, summary (short string < 20 words), "
            "pytest_exit_code, findings, human_approval_required (true)."
        )
        human_text = (
            "/no_think\n"
            f"Implementation Status: {latest_imp.status} ({latest_imp.summary})\n"
            f"Product test target: {qa_handover.product_test_target}\n"
            f"Product test exit code: {exit_code}\n"
            f"Product test output:\n{test_output[:1500]}"
        )
        text, usage, llm_error = _invoke_llm(qa_llm, system_text, human_text)
        duration = time.perf_counter() - started
        in_tok, out_tok = usage
        calls = 0 if llm_error and qa_llm is None else 1
        credits = estimate_cost_credits(
            duration_seconds=duration,
            input_tokens=in_tok,
            output_tokens=out_tok,
            calls=calls,
        )

        summary = (
            f"Product check passed ({qa_handover.product_test_target})."
            if tech_status == "passed"
            else f"Product QA failed (imp_status={latest_imp.status}, pytest_exit_code={exit_code})."
        )
        findings: list[QAFinding] = []
        summary_status: Literal["ok", "invalid_output", "unavailable"] = "ok"

        if llm_error:
            summary_status = "unavailable"
        elif text:
            try:
                parsed = _extract_json_dict(text)
                if isinstance(parsed.get("summary"), str) and parsed["summary"].strip():
                    summary = redact(parsed["summary"].strip())[:1000]
            except Exception:
                summary_status = "invalid_output"

        if not imp_succeeded:
            findings.append(
                QAFinding(
                    severity="high",
                    description=f"Implementation step failed without valid LLM output: {latest_imp.summary}",
                )
            )
        if exit_code != 0:
            findings.append(
                QAFinding(
                    severity="high",
                    description=f"Product check failed (exit_code={exit_code}): {test_output[:500]}",
                )
            )

        qa_res = QATestResult(
            status=tech_status,
            summary=summary,
            pytest_exit_code=exit_code,
            findings=findings,
            human_approval_required=True,
            summary_status=summary_status,
            run_id=step_run_id,
            trace_path=state["trace_file"],
            tool_status="completed",
        )

        append_trace(
            {
                "run_id": step_run_id,
                "workflow_id": t.workflow_id,
                "project_id": t.project_id,
                "task_id": t.task_id,
                "iteration": qa_handover.iteration,
                "agent": "qa-test-agent",
                "role": "qa_test_engineer",
                "accountable_human": role_meta.accountable_human,
                "provider": settings.llm_provider if qa_llm is None else "injected",
                "model": settings.llm_model if qa_llm is None else type(qa_llm).__name__,
                "status": qa_res.status,
                "tools": ["run_product_test_tool"],
                "pytest_target": qa_handover.product_test_target,
                "pytest_exit_code": exit_code,
                "artifact_sha256": qa_handover.artifact_sha256,
                "duration_seconds": round(duration, 4),
                "calls": calls,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "estimated_cost_credits": credits,
            },
            state["trace_file"],
        )

        q_history = list(state.get("qa_history", []))
        q_history.append(qa_res)
        feedback_parts: list[str] = []
        if not imp_succeeded:
            feedback_parts.append(latest_imp.summary)
        if exit_code != 0:
            feedback_parts.append(test_output)
        feedback_text = "\n".join(feedback_parts)
        return {"qa_history": q_history, "qa_feedback": feedback_text}

    def route_after_qa(state: DeliveryWorkflowState) -> str:
        latest_qa = state["qa_history"][-1]
        latest_imp = state["implementation_history"][-1]
        iteration = state.get("iteration", 1)
        max_loops = state["task"].max_correction_loops
        if latest_imp.status == "completed" and latest_qa.status == "passed":
            return "human_gate"
        if iteration < max_loops:
            return "implementation"
        return "human_gate"

    def human_gate_node(state: DeliveryWorkflowState) -> DeliveryWorkflowState:
        arch = state["architect_result"]
        latest_imp = state["implementation_history"][-1]
        latest_qa = state["qa_history"][-1]
        if (
            arch.status == "completed"
            and latest_imp.status == "completed"
            and bool(latest_imp.written_file)
            and latest_qa.status == "passed"
            and latest_qa.pytest_exit_code == 0
        ):
            return {"human_gate_status": "pending_approval"}
        return {"human_gate_status": "escalate_to_human"}

    builder = StateGraph(DeliveryWorkflowState)
    builder.add_node("architect", architect_node)
    builder.add_node("implementation", implementation_node)
    builder.add_node("product_qa", product_qa_node)
    builder.add_node("human_gate", human_gate_node)

    builder.add_edge(START, "architect")
    builder.add_edge("architect", "implementation")
    builder.add_edge("implementation", "product_qa")
    builder.add_conditional_edges(
        "product_qa",
        route_after_qa,
        {"implementation": "implementation", "human_gate": "human_gate"},
    )
    builder.add_edge("human_gate", END)

    graph = builder.compile()
    final_state = graph.invoke(
        {
            "task": task,
            "required_content": required_content,
            "run_dir": run_dir,
            "trace_file": trace_file,
            "initial_file_snapshot": initial_snapshot,
            "implementation_history": [],
            "qa_history": [],
            "qa_feedback": "",
            "iteration": 0,
        },
        {"recursion_limit": 25},
    )

    trace_records = [
        json.loads(line)
        for line in Path(trace_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    total_credits = round(
        sum(float(r.get("estimated_cost_credits", 0.0)) for r in trace_records),
        4,
    )
    run_ids = [str(r["run_id"]) for r in trace_records if "run_id" in r]
    latest_imp = final_state["implementation_history"][-1]
    latest_qa = final_state["qa_history"][-1]
    product_output_commit = _git_head_commit(product_root)

    manifest_path = run_dir / "manifest.json"
    report_path = run_dir / "workflow-report.json"
    patch_path = run_dir / "changes.patch"

    session_num = 3 if task.task_id.startswith("NW-S3") else 4
    manifest_payload = {
        "company": "HAW Agentic Software Factory",
        "session": session_num,
        "project_id": task.project_id,
        "customer_task_id": task.task_id,
        "team_size": 6,
        "factory_commit": factory_commit,
        "factory_code_clean": factory_code_clean,
        "product_input_commit": product_input_commit,
        "product_output_commit": product_output_commit,
        "workflow_ids": [task.workflow_id],
        "run_ids": run_ids,
        "llm_provider": settings.llm_provider if architect_llm is None else "injected",
        "llm_model": settings.llm_model if architect_llm is None else "mock",
        "model_tag_or_digest": _ollama_model_digest(settings.llm_model)
        if architect_llm is None
        else "mock",
        "test_commands": [
            "python -m pytest -q",
            f"python -m pytest {task.product_test_target} -q (in {task.product_repo_path})",
        ],
        "product_test_passed": (
            latest_imp.status == "completed" and latest_qa.status == "passed"
        ),
        "iterations_used": final_state["iteration"],
        "max_correction_loops": task.max_correction_loops,
        "mock_runs_are_separate": architect_llm is not None,
        "review_file": str(run_dir / "review.json"),
        "artifact_hashes": {
            latest_imp.written_file or task.target_product_file: latest_imp.artifact_sha256
        },
        "issue_and_pr_references": [
            f"{task.product_repo_path}/{p}" for p in task.input_files if p.startswith("docs/")
        ],
        "cost_records": "costs/usage.csv",
        "total_estimated_agent_credits": total_credits,
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    wf_result = CustomerDeliveryWorkflowResult(
        workflow_id=task.workflow_id,
        project_id=task.project_id,
        task_id=task.task_id,
        product_repo_path=str(product_root),
        factory_commit=factory_commit,
        factory_code_clean=factory_code_clean,
        product_input_commit=product_input_commit,
        product_output_commit=product_output_commit,
        iterations_used=final_state["iteration"],
        max_correction_loops=task.max_correction_loops,
        architect_result=final_state["architect_result"],
        implementation_history=final_state["implementation_history"],
        qa_history=final_state["qa_history"],
        final_qa_result=latest_qa,
        run_directory=str(run_dir),
        trace_file=trace_file,
        manifest_file=str(manifest_path),
        patch_file=str(patch_path) if patch_path.exists() else None,
        human_gate_status=final_state["human_gate_status"],
        human_approval_required=True,
        approved_by_human=None,
        total_estimated_agent_credits=total_credits,
    )
    report_path.write_text(
        wf_result.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return wf_result


def record_customer_human_review(
    report_path: Path | str,
    *,
    reviewer: str,
    decision: Literal["approved", "changes_requested", "escalate_to_human"],
    rationale: str,
    tested_source_commit: str | None = None,
    accepted_criteria: list[str] | None = None,
    open_criteria: list[str] | None = None,
) -> Path:
    """Record an explicit human review decision bound to the workflow report and product artifact SHA-256."""
    rpath = Path(report_path)
    clean_reviewer = reviewer.strip()
    if len(clean_reviewer) < 2:
        raise ValueError("A valid human reviewer name is required")
    if decision not in ("approved", "changes_requested", "escalate_to_human"):
        raise ValueError(f"Unsupported human decision: {decision}")
    if len(rationale.strip()) < 3:
        raise ValueError("A specific review rationale is required")

    raw_bytes = rpath.read_bytes()
    report = CustomerDeliveryWorkflowResult.model_validate_json(raw_bytes)
    latest_imp = report.implementation_history[-1]

    if decision == "approved":
        if report.human_gate_status != "pending_approval":
            raise ValueError(
                "Only workflows in 'pending_approval' state can be approved"
            )
        if report.architect_result.status != "completed":
            raise ValueError(
                "Cannot approve a customer delivery when the architect step did not complete"
            )
        if latest_imp.status != "completed" or not latest_imp.written_file:
            raise ValueError(
                "Cannot approve a customer delivery when the implementation step failed"
            )
        if report.final_qa_result is None or report.final_qa_result.status != "passed":
            raise ValueError(
                "Cannot approve a customer delivery when the product QA check did not pass"
            )

    artifact_hashes = {
        latest_imp.written_file or "site/index.html": latest_imp.artifact_sha256
    }

    default_ac = list(report.architect_result.handover.acceptance_criteria)
    review_record = CustomerHumanReviewRecord(
        task_id=report.task_id,
        project_id=report.project_id,
        workflow_id=report.workflow_id,
        decision=decision,
        reviewer=clean_reviewer,
        decided_at_utc=datetime.now(timezone.utc).isoformat(),
        tested_source_commit=tested_source_commit or report.product_output_commit,
        product_input_commit=report.product_input_commit,
        reviewed_artifact_hashes=artifact_hashes,
        report_path=str(rpath.resolve()),
        report_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        test_evidence_paths=[report.trace_file, report.manifest_file],
        accepted_criteria=accepted_criteria
        if accepted_criteria is not None
        else (default_ac if decision == "approved" else []),
        open_criteria=open_criteria
        if open_criteria is not None
        else (
            ["AC-09, AC-10 due in Session 5"]
            if decision == "approved"
            else default_ac
        ),
        rationale=rationale.strip(),
    )

    review_path = rpath.parent / "review.json"
    review_path.write_text(
        review_record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return review_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Customer Delivery Workflow or record a Human Gate decision."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Execute the multi-agent customer delivery workflow")
    run_cmd.add_argument("--project-id", default="website-01")
    run_cmd.add_argument("--product-repo", default=None)
    run_cmd.add_argument("--task-id", default=None)
    run_cmd.add_argument("--workflow-id", default=None)
    run_cmd.add_argument("--max-loops", type=int, default=None)
    run_cmd.add_argument(
        "--inject-fault",
        action="append",
        default=[],
        help="Controlled fault override in KEY=VALUE format (e.g. N-08_href=mailto:falsch@nordwerk.example)",
    )

    rev_cmd = sub.add_parser("review", help="Record an explicit human gate review decision")
    rev_cmd.add_argument("--report", type=Path, required=True)
    rev_cmd.add_argument("--reviewer", required=True)
    rev_cmd.add_argument(
        "--decision",
        choices=["approved", "changes_requested", "escalate_to_human"],
        required=True,
    )
    rev_cmd.add_argument("--rationale", required=True)
    rev_cmd.add_argument("--tested-commit", default=None)

    args = parser.parse_args()
    if args.command == "review":
        review_file = record_customer_human_review(
            args.report,
            reviewer=args.reviewer,
            decision=args.decision,
            rationale=args.rationale,
            tested_source_commit=args.tested_commit,
        )
        print(f"Recorded human review: {review_file}")
        return

    fault_overrides: dict[str, str] = {}
    for item in args.inject_fault:
        if "=" not in item:
            raise ValueError(f"Invalid --inject-fault '{item}', expected KEY=VALUE")
        k, v = item.split("=", 1)
        fault_overrides[k.strip()] = v.strip()

    task, _ = build_task_from_project_config(
        project_id=args.project_id,
        product_repo_path=args.product_repo,
        task_id=args.task_id,
        workflow_id=args.workflow_id,
        max_correction_loops=args.max_loops,
    )
    result = run_customer_delivery_workflow(
        task,
        project_id=args.project_id,
        fault_overrides=fault_overrides or None,
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
