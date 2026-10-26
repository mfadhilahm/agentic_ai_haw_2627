"""Session 3 Factory unit tests for project assignment, workspace sandboxing,
structured multi-agent handovers, bounded correction loops, and human gate enforcement.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_delivery_workflow import (
    DEFAULT_REQUIRED_CONTENT,
    build_task_from_project_config,
    load_project_config,
    read_product_file_tool,
    record_customer_human_review,
    run_customer_delivery_workflow,
    validate_product_workspace_path,
    write_product_file_tool,
)
from src.agents.task_models import (
    CustomerDeliveryTask,
    ProductHandoverPayload,
    QAHandoverPayload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _create_temp_product_checkout(tmp_path: Path) -> Path:
    """Create an isolated temporary customer product repository for deterministic testing."""
    product_dir = tmp_path / "client-01-website"
    (product_dir / "docs").mkdir(parents=True, exist_ok=True)
    (product_dir / "site").mkdir(parents=True, exist_ok=True)
    (product_dir / "tests").mkdir(parents=True, exist_ok=True)

    (product_dir / "docs" / "issue-01-session-03.md").write_text(
        "# Issue #1: [NW-S3-001] Nordwerk Session 3 Slice\n"
        "Scope: AC-01, AC-02 (N-03), AC-04.\n",
        encoding="utf-8",
    )
    (product_dir / "site" / "styles.css").write_text(
        "body { font-family: sans-serif; }\n", encoding="utf-8"
    )
    (product_dir / "site" / "index.html").write_text(
        "<!DOCTYPE html><html lang='de'><body>TODO_FACTORY_GENERATION</body></html>\n",
        encoding="utf-8",
    )

    real_product_test = (
        REPO_ROOT.parent / "client-01-website" / "tests" / "test_website_s3.py"
    )
    if real_product_test.is_file():
        shutil.copyfile(
            real_product_test, product_dir / "tests" / "test_website_s3.py"
        )
    else:
        (product_dir / "tests" / "test_website_s3.py").write_text(
            "from pathlib import Path\n"
            "def test_slice():\n"
            "    html = (Path(__file__).resolve().parents[1] / 'site' / 'index.html').read_text(encoding='utf-8')\n"
            "    assert 'TODO_FACTORY_GENERATION' not in html\n"
            "    assert 'Nordwerk Industrie-Service' in html\n"
            "    assert 'mailto:kontakt@nordwerk.example' in html\n",
            encoding="utf-8",
        )
    return product_dir


class FakeArchitectLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Planned Session 3 HTML structure and required German content handover.",
                    "architecture_decisions": [
                        "Single-page static HTML5 in German (lang='de').",
                        "Include N-01, N-02, N-03, N-08 mailto link, and N-09 notice.",
                    ],
                    "ready_for_implementation": True,
                }
            )
        )


class FakeValidImplementationLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Populated site/index.html with verbatim Nordwerk Session 3 strings.",
                    "company_name": DEFAULT_REQUIRED_CONTENT["N-01"],
                    "main_statement": DEFAULT_REQUIRED_CONTENT["N-02"],
                    "service_title": DEFAULT_REQUIRED_CONTENT["N-03_title"],
                    "service_description": DEFAULT_REQUIRED_CONTENT["N-03_text"],
                    "contact_label": DEFAULT_REQUIRED_CONTENT["N-08_label"],
                    "contact_href": DEFAULT_REQUIRED_CONTENT["N-08_href"],
                    "course_notice": DEFAULT_REQUIRED_CONTENT["N-09"],
                }
            )
        )


class FakeFlakyThenFixedImplementationLLM:
    """First attempt omits the required mailto target (causing QA failure); second attempt fixes it."""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content=json.dumps(
                    {
                        "summary": "Initial draft with broken contact link.",
                        "company_name": DEFAULT_REQUIRED_CONTENT["N-01"],
                        "main_statement": DEFAULT_REQUIRED_CONTENT["N-02"],
                        "service_title": DEFAULT_REQUIRED_CONTENT["N-03_title"],
                        "service_description": DEFAULT_REQUIRED_CONTENT["N-03_text"],
                        "contact_label": "Kontakt",
                        "contact_href": "mailto:wrong@example.org",
                        "course_notice": DEFAULT_REQUIRED_CONTENT["N-09"],
                    }
                )
            )
        return FakeValidImplementationLLM().invoke(messages)


class FakeAlwaysBrokenImplementationLLM:
    """Always produces incomplete HTML so bounded loop escalation can be verified."""

    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Broken draft still containing placeholder.",
                    "html_content": "<!DOCTYPE html><html lang='de'><body>TODO_FACTORY_GENERATION</body></html>",
                }
            )
        )


class FakeQALLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "summary": "Verified Nordwerk Session 3 product check.",
                    "pytest_exit_code": 0,
                    "findings": [],
                    "human_approval_required": True,
                }
            )
        )


def test_project_configuration_and_task_assignment() -> None:
    """D1 / A1: Verify project configuration loads website-01 and maps to CustomerDeliveryTask."""
    cfg = load_project_config("website-01")
    assert cfg["project_id"] == "website-01"
    assert cfg["customer_task_id"] == "NW-S3-001"
    assert cfg["product_repo_path"] == "../client-01-website"
    assert cfg["allowed_write_prefixes"] == ["site/"]

    task, req_content = build_task_from_project_config("website-01")
    assert isinstance(task, CustomerDeliveryTask)
    assert task.project_id == "website-01"
    assert task.task_id == "NW-S3-001"
    assert task.target_product_file == "site/index.html"
    assert req_content["N-01"] == "Nordwerk Industrie-Service"
    assert req_content["N-08_href"] == "mailto:kontakt@nordwerk.example"


def test_product_workspace_sandbox_enforces_allowed_boundaries(tmp_path: Path) -> None:
    """A4: Verify product tools allow writes in site/ and reject path traversal, secrets, and tests/."""
    product_dir = _create_temp_product_checkout(tmp_path)

    rel_written, sha = write_product_file_tool(
        product_dir,
        "site/index.html",
        "<!DOCTYPE html><html lang='de'><body>Updated</body></html>",
        allowed_write_prefixes=["site/"],
    )
    assert rel_written == "site/index.html"
    assert len(sha) == 64
    assert "Updated" in read_product_file_tool(product_dir, "site/index.html")

    # 1. Reject path traversal escaping the product repository
    with pytest.raises(ValueError, match="escapes configured product workspace"):
        validate_product_workspace_path(product_dir, "../factory_file.py", for_write=False)

    with pytest.raises(ValueError, match="escapes configured product workspace"):
        write_product_file_tool(product_dir, "../hack.txt", "bad")

    # 2. Reject secret files (.env*) and .git internals
    with pytest.raises(ValueError, match="protected path"):
        write_product_file_tool(product_dir, ".env", "SECRET=1")

    with pytest.raises(ValueError, match="protected path"):
        read_product_file_tool(product_dir, ".git/config")

    # 3. Reject writing outside allowed_write_prefixes (e.g. modifying product tests or README)
    with pytest.raises(ValueError, match="outside allowed product directories"):
        write_product_file_tool(
            product_dir,
            "tests/test_website_s3.py",
            "# overwritten test",
            allowed_write_prefixes=["site/"],
        )


def test_structured_handover_and_end_to_end_delivery_workflow(tmp_path: Path) -> None:
    """A2, A3, D1: Verify Architect -> Implementation -> QA structured handovers and human review."""
    product_dir = _create_temp_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    task = CustomerDeliveryTask(
        task_id="NW-S3-TEST-01",
        workflow_id="WF-S3-TEST-01",
        project_id="website-01",
        product_repo_path=str(product_dir),
        max_correction_loops=2,
    )

    result = run_customer_delivery_workflow(
        task,
        architect_llm=FakeArchitectLLM(),
        implementation_llm=FakeValidImplementationLLM(),
        qa_llm=FakeQALLM(),
        runs_root=runs_dir,
    )

    assert result.iterations_used == 1
    assert result.human_gate_status == "pending_approval"
    assert result.approved_by_human is None
    assert isinstance(result.architect_result.handover, ProductHandoverPayload)
    assert result.architect_result.handover.to_role == "backend_api_engineer"

    assert len(result.implementation_history) == 1
    imp_step = result.implementation_history[0]
    assert imp_step.written_file == "site/index.html"
    assert isinstance(imp_step.handover, QAHandoverPayload)
    assert imp_step.handover.to_role == "qa_test_engineer"
    assert imp_step.handover.artifact_sha256 == imp_step.artifact_sha256

    assert result.final_qa_result is not None
    assert result.final_qa_result.status == "passed"
    assert result.final_qa_result.pytest_exit_code == 0

    # Verify manifest and patch exist in run directory
    manifest = json.loads(Path(result.manifest_file).read_text(encoding="utf-8"))
    assert manifest["project_id"] == "website-01"
    assert manifest["product_test_passed"] is True
    assert len(manifest["run_ids"]) == 3

    # Record explicit human gate approval
    report_path = Path(result.run_directory) / "workflow-report.json"
    review_path = record_customer_human_review(
        report_path,
        reviewer="saad",
        decision="approved",
        rationale="Checked AC-01, AC-02 (N-03), and AC-04 mailto link in site/index.html.",
    )
    review_data = json.loads(review_path.read_text(encoding="utf-8"))
    assert review_data["decision"] == "approved"
    assert review_data["reviewer"] == "saad"
    assert review_data["reviewed_artifact_hashes"]["site/index.html"] == imp_step.artifact_sha256


def test_bounded_correction_loop_recovers_and_escalates_when_exhausted(
    tmp_path: Path,
) -> None:
    """A4: Verify correction loop retries on QA failure and escalates to human when limit reached."""
    product_dir = _create_temp_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    # Case 1: Fails on iteration 1, succeeds on iteration 2
    flaky_llm = FakeFlakyThenFixedImplementationLLM()
    task_recover = CustomerDeliveryTask(
        task_id="NW-S3-RECOVER",
        workflow_id="WF-S3-RECOVER",
        project_id="website-01",
        product_repo_path=str(product_dir),
        max_correction_loops=2,
    )
    res_recover = run_customer_delivery_workflow(
        task_recover,
        architect_llm=FakeArchitectLLM(),
        implementation_llm=flaky_llm,
        qa_llm=FakeQALLM(),
        runs_root=runs_dir,
    )
    assert res_recover.iterations_used == 2
    assert len(res_recover.qa_history) == 2
    assert res_recover.qa_history[0].status == "failed"
    assert res_recover.qa_history[1].status == "passed"
    assert res_recover.human_gate_status == "pending_approval"

    # Case 2: Fails all iterations up to max_correction_loops=2 -> escalates to human
    task_escalate = CustomerDeliveryTask(
        task_id="NW-S3-ESCALATE",
        workflow_id="WF-S3-ESCALATE",
        project_id="website-01",
        product_repo_path=str(product_dir),
        max_correction_loops=2,
    )
    res_escalate = run_customer_delivery_workflow(
        task_escalate,
        architect_llm=FakeArchitectLLM(),
        implementation_llm=FakeAlwaysBrokenImplementationLLM(),
        qa_llm=FakeQALLM(),
        runs_root=runs_dir,
    )
    assert res_escalate.iterations_used == 2
    assert len(res_escalate.qa_history) == 2
    assert all(q.status == "failed" for q in res_escalate.qa_history)
    assert res_escalate.human_gate_status == "escalate_to_human"

    report_path = Path(res_escalate.run_directory) / "workflow-report.json"
    with pytest.raises(ValueError, match="pending_approval"):
        record_customer_human_review(
            report_path,
            reviewer="felix",
            decision="approved",
            rationale="Should not be allowed to approve failed QA.",
        )
