"""Session 3 & 4 Customer Delivery Workflow:
Multi-agent cooperation (Architect -> Implementation -> QA) on an external product checkout
with workspace sandboxing, strict LLM output validation (no silent HTML fallback),
verified clean Factory commit tracking, bounded correction loops, run manifests,
and a human review gate.
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

DEFAULT_REQUIRED_CONTENT: dict[str, str] = {
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

SESSION_04_REQUIRED_CONTENT: dict[str, str] = {
    **DEFAULT_REQUIRED_CONTENT,
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
    "N-06_group_1": "Kleine Produktionsbetriebe",
    "N-06_group_2": "Technische Serviceunternehmen",
    "N-07": (
        "Ein fester Ansprechpartner, ein gemeinsam vereinbarter Leistungsumfang "
        "und nachvollziehbare Ergebnisse."
    ),
}


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
    factory_commit_clean: bool = True
    factory_dirty_files: list[str] = Field(default_factory=list)
    workflow_code_sha256: str = ""
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
    acceptance_criteria: list[str]
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
    req_content = dict(DEFAULT_REQUIRED_CONTENT)
    if isinstance(cfg.get("required_content"), dict):
        req_content.update(
            {str(k): str(v) for k, v in cfg["required_content"].items()}
        )

    resolved_task_id = task_id or str(cfg.get("customer_task_id", "NW-S4-001"))
    description = (
        f"Deliver Nordwerk Industrie-Service website release candidate ({resolved_task_id}) "
        "in the customer repository."
    )
    product_test_target = str(
        cfg.get("product_test_target", "tests/test_website_s3.py")
    )

    # Support R-01 reference baseline task directly from configuration (C1 / L4.4)
    r01_cfg = cfg.get("r01_reference_task")
    if (
        isinstance(r01_cfg, dict)
        and resolved_task_id.upper().startswith("R-01")
    ):
        if isinstance(r01_cfg.get("description"), str) and r01_cfg["description"].strip():
            description = r01_cfg["description"].strip()
        if isinstance(r01_cfg.get("additional_required_content"), dict):
            req_content.update(
                {
                    str(k): str(v)
                    for k, v in r01_cfg["additional_required_content"].items()
                }
            )
        if isinstance(r01_cfg.get("product_test_target"), str):
            product_test_target = r01_cfg["product_test_target"]

    task = CustomerDeliveryTask(
        task_id=resolved_task_id,
        description=description,
        workflow_id=workflow_id or f"WF-{project_id.upper()}-{uuid.uuid4().hex[:8]}",
        project_id=str(cfg.get("project_id", project_id)),
        product_repo_path=product_repo_path
        or str(cfg.get("product_repo_path", "../client-01-website")),
        input_files=list(
            cfg.get(
                "product_input_files",
                ["docs/issue-01-session-03.md", "site/index.html"],
            )
        ),
        target_product_file=str(cfg.get("target_product_file", "site/index.html")),
        product_test_target=product_test_target,
        allowed_write_prefixes=list(cfg.get("allowed_write_prefixes", ["site/"])),
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


def _get_factory_git_state(
    repo_dir: Path = REPO_ROOT,
    tracked_code_paths: tuple[str, ...] = ("src", "config", "organization"),
) -> tuple[str, bool, list[str]]:
    """Return (head_commit, is_clean, dirty_files) for Factory workflow code & config.

    Ensures the recorded factory_commit genuinely contains the executed workflow code
    and project configuration (Session 3 Feedback item 2).
    """
    head_commit = _git_head_commit(repo_dir)
    dirty_files: list[str] = []
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "--", *tracked_code_paths],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if completed.returncode == 0:
            for line in completed.stdout.splitlines():
                stripped = line.strip()
                if stripped:
                    dirty_files.append(stripped)
    except Exception:
        pass
    return head_commit, len(dirty_files) == 0, dirty_files


def _compute_workflow_code_sha256(project_id: str = "website-01") -> str:
    """Compute a deterministic SHA-256 over the workflow module and project config."""
    hasher = hashlib.sha256()
    workflow_file = Path(__file__).resolve()
    if workflow_file.is_file():
        hasher.update(workflow_file.read_bytes())
    cfg_file = PROJECTS_CONFIG_DIR / f"{project_id}.yaml"
    if cfg_file.is_file():
        hasher.update(cfg_file.read_bytes())
    return hasher.hexdigest()


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
    min_output_tokens: int = 1024,
) -> tuple[str | None, tuple[int | None, int | None], str | None]:
    try:
        if llm is not None:
            model = llm
        else:
            base_settings = get_settings()
            effective_settings = base_settings.model_copy(
                update={
                    "llm_max_output_tokens": max(
                        base_settings.llm_max_output_tokens, min_output_tokens
                    )
                }
            )
            model = get_chat_model(
                effective_settings, reasoning=False, json_mode=True
            )
        response = model.invoke(
            [SystemMessage(content=system_text), HumanMessage(content=human_text)]
        )
        return _message_text(response), usage_from_message(response), None
    except Exception as exc:
        return None, (None, None), f"{type(exc).__name__}: {exc}"


def _record_step_trace(
    record: dict[str, Any],
    *,
    run_dir: Path,
    trace_file: str,
) -> None:
    """Write trace record both to the workflow trace.jsonl and to a per-run_id <run_id>.jsonl file."""
    append_trace(record, trace_file)
    run_id = str(record["run_id"])
    append_trace(record, str(run_dir / f"{run_id}.jsonl"))


def _validate_and_normalize_implementation_fields(
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Validate structured LLM output fields without any fallback to DEFAULT_REQUIRED_CONTENT.

    Raises ValueError if the LLM response is empty or missing required core fields,
    preventing failed or unparseable LLM calls from being masked by default HTML.
    """
    if not isinstance(fields, dict) or not fields:
        raise ValueError("LLM implementation output is empty or not a JSON object")

    if isinstance(fields.get("html_content"), str) and fields["html_content"].strip():
        return {"html_content": fields["html_content"].strip()}

    merged: dict[str, Any] = {}
    for nested_key in ("required_content", "content"):
        nested = fields.get(nested_key)
        if isinstance(nested, dict):
            merged.update(nested)
    merged.update(fields)

    def _clean_str(keys: tuple[str, ...]) -> str:
        for k in keys:
            val = merged.get(k)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    company_name = _clean_str(("company_name", "N-01"))
    main_statement = _clean_str(("main_statement", "N-02"))
    contact_label = _clean_str(("contact_label", "N-08_label"))
    contact_href = _clean_str(("contact_href", "N-08_href"))
    course_notice = _clean_str(("course_notice", "N-09"))

    services: list[tuple[str, str]] = []
    raw_services = merged.get("services")
    if isinstance(raw_services, list):
        for item in raw_services:
            if isinstance(item, dict):
                t_val = str(item.get("title") or "").strip()
                d_val = str(
                    item.get("description") or item.get("text") or ""
                ).strip()
                if t_val and d_val:
                    services.append((t_val, d_val))

    service_key_pairs = (
        (("service_title", "N-03_title"), ("service_description", "N-03_text")),
        (("service_2_title", "N-04_title"), ("service_2_description", "N-04_text")),
        (("service_3_title", "N-05_title"), ("service_3_description", "N-05_text")),
        (("service_4_title", "R-01_title"), ("service_4_description", "R-01_text")),
    )
    existing_titles = {t for t, _ in services}
    for title_keys, desc_keys in service_key_pairs:
        t_val = _clean_str(title_keys)
        d_val = _clean_str(desc_keys)
        if t_val and d_val and t_val not in existing_titles:
            services.append((t_val, d_val))
            existing_titles.add(t_val)

    target_groups: list[str] = []
    raw_groups = merged.get("target_groups")
    if isinstance(raw_groups, list):
        for g in raw_groups:
            if isinstance(g, str) and g.strip():
                target_groups.append(g.strip())
    for g_key in ("N-06_group_1", "target_group_1", "N-06_group_2", "target_group_2"):
        g_val = _clean_str((g_key,))
        if g_val and g_val not in target_groups:
            target_groups.append(g_val)

    working_approach = _clean_str(("working_approach", "N-07"))

    missing: list[str] = []
    if not company_name:
        missing.append("company_name (N-01)")
    if not main_statement:
        missing.append("main_statement (N-02)")
    if not services:
        missing.append("services / service_title+service_description (N-03..N-05)")
    if not contact_label:
        missing.append("contact_label (N-08_label)")
    if not contact_href:
        missing.append("contact_href (N-08_href)")
    if not course_notice:
        missing.append("course_notice (N-09)")

    if missing:
        raise ValueError(
            "LLM implementation output is missing required fields (no default HTML fallback allowed): "
            + ", ".join(missing)
        )

    return {
        "company_name": company_name,
        "main_statement": main_statement,
        "services": services,
        "target_groups": target_groups,
        "working_approach": working_approach,
        "contact_label": contact_label,
        "contact_href": contact_href,
        "course_notice": course_notice,
    }


def _render_html_document(fields: dict[str, Any]) -> str:
    """Render clean semantic German HTML5 strictly from validated LLM output fields.

    Raises ValueError if fields are missing or invalid; never substitutes DEFAULT_REQUIRED_CONTENT.
    """
    normalized = _validate_and_normalize_implementation_fields(fields)
    if "html_content" in normalized:
        return str(normalized["html_content"])

    company_name = normalized["company_name"]
    main_statement = normalized["main_statement"]
    services: list[tuple[str, str]] = normalized["services"]
    target_groups: list[str] = normalized["target_groups"]
    working_approach: str = normalized["working_approach"]
    contact_label = normalized["contact_label"]
    contact_href = normalized["contact_href"]
    course_notice = normalized["course_notice"]

    nav_items = ['<li><a href="#leistungen">Leistungen</a></li>']
    if target_groups:
        nav_items.append('<li><a href="#zielgruppen">Zielgruppen</a></li>')
    if working_approach:
        nav_items.append('<li><a href="#arbeitsweise">Arbeitsweise</a></li>')
    nav_items.append('<li><a href="#kontakt">Kontakt</a></li>')
    nav_list_html = "\n        ".join(nav_items)

    service_cards_html = "\n".join(
        f"""      <article class="service-card">
        <h3>{title}</h3>
        <p>{desc}</p>
      </article>"""
        for title, desc in services
    )

    target_groups_section = ""
    if target_groups:
        groups_li = "\n".join(
            f'        <li class="target-group-item">{group}</li>'
            for group in target_groups
        )
        target_groups_section = f"""
    <section class="target-groups" id="zielgruppen" aria-labelledby="zielgruppen-heading">
      <h2 id="zielgruppen-heading">Für wen wir arbeiten</h2>
      <p>Unsere Unterstützung richtet sich gezielt an:</p>
      <ul class="target-group-list">
{groups_li}
      </ul>
    </section>
"""

    working_approach_section = ""
    if working_approach:
        working_approach_section = f"""
    <section class="working-approach" id="arbeitsweise" aria-labelledby="arbeitsweise-heading">
      <h2 id="arbeitsweise-heading">Unsere Arbeitsweise</h2>
      <p class="approach-statement">{working_approach}</p>
    </section>
"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{company_name} – Technischer Betrieb &amp; Industrieservice</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <a class="skip-link" href="#main-content">Zum Hauptinhalt springen</a>

  <div class="course-notice" role="note" aria-label="Übungshinweis">
    {course_notice}
  </div>

  <header class="site-header">
    <div class="container header-inner">
      <span class="brand-name">{company_name}</span>
      <nav class="site-nav" aria-label="Hauptnavigation">
        <ul class="nav-list">
        {nav_list_html}
        </ul>
      </nav>
    </div>
  </header>

  <main class="container" id="main-content">
    <section class="hero" id="start" aria-labelledby="hero-heading">
      <h1 id="hero-heading">{company_name}</h1>
      <p class="lead">{main_statement}</p>
      <p class="hero-actions">
        <a class="cta-link" href="{contact_href}">{contact_label}</a>
      </p>
    </section>

    <section class="services" id="leistungen" aria-labelledby="leistungen-heading">
      <h2 id="leistungen-heading">Unsere Leistungen im Überblick</h2>
      <div class="service-grid">
{service_cards_html}
      </div>
    </section>{target_groups_section}{working_approach_section}
    <section class="contact" id="kontakt" aria-labelledby="kontakt-heading">
      <h2 id="kontakt-heading">Kontakt</h2>
      <p>Sie möchten unverbindlich Informationen anfordern? Kontaktieren Sie uns direkt per E-Mail:</p>
      <a class="cta-link" href="{contact_href}">{contact_label}</a>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>&copy; 2026 {company_name} · Hamburg</p>
    </div>
  </footer>
</body>
</html>
"""


def run_customer_delivery_workflow(
    task: CustomerDeliveryTask | None = None,
    *,
    project_id: str = "website-01",
    required_content: dict[str, str] | None = None,
    architect_llm: Any | None = None,
    implementation_llm: Any | None = None,
    qa_llm: Any | None = None,
    runs_root: Path | None = None,
    enforce_clean_factory_commit: bool | None = None,
) -> CustomerDeliveryWorkflowResult:
    """Execute the multi-agent customer delivery workflow on the external product repo."""
    cfg_acceptance_criteria = ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05", "AC-06", "AC-07", "AC-08"]
    try:
        cfg_data = load_project_config(project_id)
        if isinstance(cfg_data.get("acceptance_criteria_in_scope"), list):
            cfg_acceptance_criteria = [
                str(x) for x in cfg_data["acceptance_criteria_in_scope"]
            ]
    except Exception:
        pass

    if task is None:
        task, loaded_req_content = build_task_from_project_config(project_id=project_id)
        if required_content is None:
            required_content = loaded_req_content
    elif required_content is None:
        required_content = dict(DEFAULT_REQUIRED_CONTENT)

    is_mock_run = (
        architect_llm is not None
        or implementation_llm is not None
        or qa_llm is not None
    )
    if enforce_clean_factory_commit is None:
        enforce_clean_factory_commit = not is_mock_run

    factory_commit, factory_commit_clean, factory_dirty_files = _get_factory_git_state(
        REPO_ROOT
    )
    if enforce_clean_factory_commit and not factory_commit_clean:
        raise RuntimeError(
            "Factory repository has uncommitted changes in workflow code or config "
            f"({factory_dirty_files}). Commit all Factory changes before executing a "
            "delivery run so factory_commit matches the executed workflow code."
        )

    workflow_code_sha256 = _compute_workflow_code_sha256(task.project_id)
    settings = get_settings()
    product_root = resolve_product_repo_root(task.product_repo_path)
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
        ac_list = state["acceptance_criteria"]
        role_meta = load_role_metadata("software_architect")
        step_run_id = str(uuid.uuid4())
        started = time.perf_counter()
        tools_used: list[str] = []
        loaded_files: dict[str, str] = {}

        for rel_path in t.input_files:
            loaded_files[rel_path] = read_product_file_tool(product_root, rel_path)
            if "read_product_file_tool" not in tools_used:
                tools_used.append("read_product_file_tool")

        system_text = (
            "You are the Software Architect agent planning customer delivery "
            "for Nordwerk Industrie-Service. Return ONLY valid JSON with keys: "
            "architecture_decisions (non-empty list of strings), "
            "ready_for_implementation (true), and summary (concise string under 25 words)."
        )
        human_text = (
            "/no_think\n"
            f"Project ID: {t.project_id}\n"
            f"Task ID: {t.task_id}\n"
            f"Target File: {t.target_product_file}\n"
            f"Acceptance Criteria: {json.dumps(ac_list)}\n"
            f"Required Verbatim Strings:\n{json.dumps(req_map, ensure_ascii=False, indent=2)}\n"
            f"Customer Issue Excerpt:\n{loaded_files.get(t.input_files[0], '')[:1500]}"
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
        status: Literal["completed", "needs_review", "error"] = "error"
        ready_for_imp = False

        if llm_error:
            status = "error"
            summary = f"Architect LLM invocation failed: {llm_error}"
        elif not text or not text.strip():
            status = "error"
            summary = "Architect LLM returned an empty response."
        else:
            try:
                parsed = _extract_json_dict(text)
                raw_summary = parsed.get("summary")
                raw_decisions = parsed.get("architecture_decisions")
                if isinstance(raw_decisions, list):
                    decisions = [
                        str(x).strip() for x in raw_decisions if str(x).strip()
                    ]
                if isinstance(raw_summary, str) and raw_summary.strip() and decisions:
                    summary = raw_summary.strip()
                    ready_for_imp = bool(parsed.get("ready_for_implementation", True))
                    status = "completed" if ready_for_imp else "needs_review"
                else:
                    status = "error"
                    summary = (
                        "Architect LLM JSON is missing required non-empty 'summary' "
                        "or 'architecture_decisions'."
                    )
            except Exception as exc:
                status = "error"
                summary = f"Architect LLM output is not valid JSON: {type(exc).__name__}: {exc}"

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
            ready_for_implementation=ready_for_imp,
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

        _record_step_trace(
            {
                "run_id": step_run_id,
                "workflow_id": t.workflow_id,
                "project_id": t.project_id,
                "task_id": t.task_id,
                "factory_commit": factory_commit,
                "factory_commit_clean": factory_commit_clean,
                "workflow_code_sha256": workflow_code_sha256,
                "agent": role_meta.agent_id,
                "role": "software_architect",
                "accountable_human": role_meta.accountable_human,
                "provider": settings.llm_provider if architect_llm is None else "injected",
                "model": settings.llm_model if architect_llm is None else type(architect_llm).__name__,
                "status": plan_res.status,
                "summary": plan_res.summary,
                "tools": tools_used,
                "handover_to": handover.to_role,
                "ready_for_implementation": ready_for_imp,
                "duration_seconds": plan_res.duration_seconds,
                "calls": calls,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "estimated_cost_credits": credits,
            },
            run_dir=state["run_dir"],
            trace_file=state["trace_file"],
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

        if not handover.ready_for_implementation or state["architect_result"].status != "completed":
            duration = time.perf_counter() - started
            qa_handover = QAHandoverPayload(
                from_agent=role_meta.agent_id,
                from_role="backend_api_engineer",
                to_role="qa_test_engineer",
                project_id=t.project_id,
                task_id=t.task_id,
                workflow_id=t.workflow_id,
                product_repo_path=str(product_root),
                modified_files=[],
                artifact_sha256="",
                product_test_target=t.product_test_target,
                acceptance_criteria=handover.acceptance_criteria,
                iteration=iteration,
                ready_for_qa=False,
            )
            imp_res = ImplementationStepResult(
                run_id=step_run_id,
                iteration=iteration,
                agent=role_meta.agent_id,
                role="backend_api_engineer",
                accountable_human=role_meta.accountable_human,
                status="error",
                summary="Skipped implementation because architect handover was not ready.",
                written_file=None,
                artifact_sha256="",
                patch_path=None,
                handover=qa_handover,
                tools_used=[],
                duration_seconds=round(duration, 4),
                input_tokens=None,
                output_tokens=None,
                estimated_cost_credits=0.0,
            )
            history = list(state.get("implementation_history", []))
            history.append(imp_res)
            return {
                "iteration": iteration,
                "qa_handover": qa_handover,
                "implementation_history": history,
            }

        expected_keys = list(handover.required_content.keys())
        system_text = (
            "You are the Implementation Engineer agent generating the Nordwerk Industrie-Service "
            "website from the structured ProductHandoverPayload. "
            "Return ONLY a valid JSON object containing every key from required_content copied "
            "verbatim in German, plus a concise 'summary' key (under 15 words) at the end. "
            "Do not omit any key from required_content and do not invent unrequested claims."
        )
        compact_handover = {
            "task_id": handover.task_id,
            "target_product_file": handover.target_product_file,
            "acceptance_criteria": handover.acceptance_criteria,
            "required_content": handover.required_content,
            "required_json_keys": [*expected_keys, "summary"],
        }
        human_text = (
            "/no_think\n"
            f"Iteration: {iteration} of {t.max_correction_loops}\n"
            f"Handover Contract:\n{json.dumps(compact_handover, ensure_ascii=False, indent=2)}\n"
        )
        if feedback:
            human_text += f"\nPrevious QA/Validation Failure Feedback to Fix:\n{feedback}\n"

        text, usage, llm_error = _invoke_llm(
            implementation_llm, system_text, human_text, min_output_tokens=1024
        )
        in_tok, out_tok = usage
        calls = 0 if llm_error and implementation_llm is None else 1

        written_rel: str | None = None
        sha256_hex = ""
        patch_path_str: str | None = None
        tools_used: list[str] = []
        ready_for_qa = False
        status: Literal["completed", "needs_review", "error"] = "error"
        summary = ""

        if llm_error:
            status = "error"
            summary = f"Implementation LLM invocation failed: {llm_error}"
        elif not text or not text.strip():
            status = "error"
            summary = "Implementation LLM returned an empty response."
        else:
            try:
                parsed_fields = _extract_json_dict(text)
                html_content = _render_html_document(parsed_fields)
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
                patch_path_str = str(patch_file)
                raw_summary = parsed_fields.get("summary")
                summary = (
                    raw_summary.strip()
                    if isinstance(raw_summary, str) and raw_summary.strip()
                    else f"Generated {t.target_product_file} from validated LLM fields (iteration {iteration})."
                )
                status = "completed"
                ready_for_qa = True
            except Exception as exc:
                status = "error"
                summary = f"Implementation LLM output validation failed: {type(exc).__name__}: {exc}"

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
            patch_path=patch_path_str,
            handover=qa_handover,
            tools_used=tools_used,
            duration_seconds=round(duration, 4),
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_credits=credits,
        )

        _record_step_trace(
            {
                "run_id": step_run_id,
                "workflow_id": t.workflow_id,
                "project_id": t.project_id,
                "task_id": t.task_id,
                "factory_commit": factory_commit,
                "factory_commit_clean": factory_commit_clean,
                "workflow_code_sha256": workflow_code_sha256,
                "iteration": iteration,
                "agent": role_meta.agent_id,
                "role": "backend_api_engineer",
                "accountable_human": role_meta.accountable_human,
                "provider": settings.llm_provider if implementation_llm is None else "injected",
                "model": settings.llm_model if implementation_llm is None else type(implementation_llm).__name__,
                "status": imp_res.status,
                "summary": imp_res.summary,
                "tools": tools_used,
                "written_file": written_rel,
                "artifact_sha256": sha256_hex,
                "handover_to": qa_handover.to_role,
                "ready_for_qa": ready_for_qa,
                "duration_seconds": imp_res.duration_seconds,
                "calls": calls,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "estimated_cost_credits": credits,
            },
            run_dir=state["run_dir"],
            trace_file=state["trace_file"],
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

        imp_ok = latest_imp.status == "completed" and qa_handover.ready_for_qa
        tech_status: Literal["passed", "failed", "needs_review", "error"] = (
            "passed" if (exit_code == 0 and imp_ok) else "failed"
        )

        system_text = (
            "You are the QA & Test Engineer agent verifying the Nordwerk customer product check. "
            "Return ONLY valid JSON with keys: status, summary, pytest_exit_code, findings, "
            "human_approval_required (true)."
        )
        human_text = (
            "/no_think\n"
            f"QA Handover:\n{qa_handover.model_dump_json(indent=2)}\n"
            f"Implementation step status: {latest_imp.status} ({latest_imp.summary})\n"
            f"Product test exit code: {exit_code}\n"
            f"Product test output:\n{test_output}"
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
            "Product check passed for configured acceptance criteria."
            if tech_status == "passed"
            else f"Product QA failed (implementation_status={latest_imp.status}, pytest_exit_code={exit_code})."
        )
        findings: list[QAFinding] = []
        summary_status: Literal["ok", "invalid_output", "unavailable"] = "ok"

        if llm_error:
            summary_status = "unavailable"
            if tech_status == "passed":
                tech_status = "needs_review"
        elif not text or not text.strip():
            summary_status = "invalid_output"
            if tech_status == "passed":
                tech_status = "needs_review"
        else:
            try:
                parsed = _extract_json_dict(text)
                if isinstance(parsed.get("summary"), str) and parsed["summary"].strip():
                    summary = redact(parsed["summary"].strip())[:1000]
                else:
                    summary_status = "invalid_output"
                    if tech_status == "passed":
                        tech_status = "needs_review"
            except Exception:
                summary_status = "invalid_output"
                if tech_status == "passed":
                    tech_status = "needs_review"

        if not imp_ok:
            findings.append(
                QAFinding(
                    severity="high",
                    description=f"Implementation step did not complete validly: {latest_imp.summary}",
                )
            )

        if exit_code != 0:
            findings.append(
                QAFinding(
                    severity="high",
                    description=f"Product check failed: {test_output[:500]}",
                )
            )

        qa_res = QATestResult(
            status=tech_status,
            summary=summary,
            pytest_exit_code=exit_code if imp_ok else (exit_code or 1),
            findings=findings,
            human_approval_required=True,
            summary_status=summary_status,
            run_id=step_run_id,
            trace_path=state["trace_file"],
            tool_status="completed",
        )

        _record_step_trace(
            {
                "run_id": step_run_id,
                "workflow_id": t.workflow_id,
                "project_id": t.project_id,
                "task_id": t.task_id,
                "factory_commit": factory_commit,
                "factory_commit_clean": factory_commit_clean,
                "workflow_code_sha256": workflow_code_sha256,
                "iteration": qa_handover.iteration,
                "agent": "qa-test-agent",
                "role": "qa_test_engineer",
                "accountable_human": role_meta.accountable_human,
                "provider": settings.llm_provider if qa_llm is None else "injected",
                "model": settings.llm_model if qa_llm is None else type(qa_llm).__name__,
                "status": qa_res.status,
                "summary": qa_res.summary,
                "summary_status": summary_status,
                "tools": ["run_product_test_tool"],
                "pytest_target": qa_handover.product_test_target,
                "pytest_exit_code": qa_res.pytest_exit_code,
                "artifact_sha256": qa_handover.artifact_sha256,
                "duration_seconds": round(duration, 4),
                "calls": calls,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "estimated_cost_credits": credits,
            },
            run_dir=state["run_dir"],
            trace_file=state["trace_file"],
        )

        q_history = list(state.get("qa_history", []))
        q_history.append(qa_res)
        feedback_parts: list[str] = []
        if not imp_ok:
            feedback_parts.append(latest_imp.summary)
        if exit_code != 0:
            feedback_parts.append(test_output)
        return {"qa_history": q_history, "qa_feedback": "\n".join(feedback_parts)}

    def route_after_qa(state: DeliveryWorkflowState) -> str:
        arch_ok = state["architect_result"].status == "completed"
        latest_imp = state["implementation_history"][-1]
        latest_qa = state["qa_history"][-1]
        iteration = state.get("iteration", 1)
        max_loops = state["task"].max_correction_loops
        if arch_ok and latest_imp.status == "completed" and latest_qa.status == "passed":
            return "human_gate"
        if arch_ok and iteration < max_loops:
            return "implementation"
        return "human_gate"

    def human_gate_node(state: DeliveryWorkflowState) -> DeliveryWorkflowState:
        arch_ok = state["architect_result"].status == "completed"
        latest_imp = state["implementation_history"][-1]
        latest_qa = state["qa_history"][-1]
        if (
            arch_ok
            and latest_imp.status == "completed"
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
            "acceptance_criteria": cfg_acceptance_criteria,
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

    manifest_payload = {
        "company": "HAW Agentic Software Factory",
        "session": 4,
        "project_id": task.project_id,
        "customer_task_id": task.task_id,
        "team_size": 6,
        "factory_commit": factory_commit,
        "factory_commit_clean": factory_commit_clean,
        "factory_dirty_files": factory_dirty_files,
        "workflow_code_sha256": workflow_code_sha256,
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
        "mock_runs_are_separate": is_mock_run,
        "review_file": str(run_dir / "review.json"),
        "artifact_hashes": {
            latest_imp.written_file or task.target_product_file: latest_imp.artifact_sha256
        }
        if latest_imp.written_file
        else {},
        "issue_and_pr_references": [
            f"{task.product_repo_path}/{inp}" for inp in task.input_files if inp.startswith("docs/")
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
        factory_commit_clean=factory_commit_clean,
        factory_dirty_files=factory_dirty_files,
        workflow_code_sha256=workflow_code_sha256,
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

    artifact_hashes = (
        {latest_imp.written_file: latest_imp.artifact_sha256}
        if latest_imp.written_file
        else {}
    )

    default_accepted = (
        list(report.architect_result.handover.acceptance_criteria)
        if decision == "approved"
        else []
    )
    default_open = (
        ["AC-09, AC-10 due in Session 5"]
        if decision == "approved"
        else list(report.architect_result.handover.acceptance_criteria)
    )

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
        else default_accepted,
        open_criteria=open_criteria
        if open_criteria is not None
        else default_open,
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
        "--allow-dirty-factory",
        action="store_true",
        help="Allow running even when Factory src/ or config/ has uncommitted changes (not for evidence runs).",
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

    task, req_content = build_task_from_project_config(
        project_id=args.project_id,
        product_repo_path=args.product_repo,
        task_id=args.task_id,
        workflow_id=args.workflow_id,
        max_correction_loops=args.max_loops,
    )
    result = run_customer_delivery_workflow(
        task,
        project_id=args.project_id,
        required_content=req_content,
        enforce_clean_factory_commit=not args.allow_dirty_factory,
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
