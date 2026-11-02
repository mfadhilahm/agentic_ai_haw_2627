"""Session 4 Factory unit tests verifying:
1. Session 3 feedback fix #1: Failed, truncated, or incomplete LLM output is never masked by default HTML.
2. Session 3 feedback fix #2: Clean factory_commit verification and workflow_code_sha256 tracking.
3. Session 4 Quality Gate (A3, A4): Controlled contact/link fault detection, gate blocking, and recovery.
4. Session 4 R-01 Baseline task configuration and 4-service rendering (C1, L4.4).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_delivery_workflow import (
    SESSION_04_REQUIRED_CONTENT,
    _compute_workflow_code_sha256,
    _render_html_document,
    build_task_from_project_config,
    record_customer_human_review,
    run_customer_delivery_workflow,
)
from src.agents.task_models import CustomerDeliveryTask


def _create_s4_temp_product_checkout(tmp_path: Path) -> Path:
    """Create an isolated temporary customer product repository with Session 4 checks (AC-01..AC-08)."""
    product_dir = tmp_path / "client-01-website"
    (product_dir / "docs").mkdir(parents=True, exist_ok=True)
    (product_dir / "site").mkdir(parents=True, exist_ok=True)
    (product_dir / "tests").mkdir(parents=True, exist_ok=True)

    (product_dir / "docs" / "issue-01-session-03.md").write_text(
        "# Issue #2: [NW-S4-001] Nordwerk Session 4 Release Candidate (AC-01..AC-08)\n",
        encoding="utf-8",
    )
    (product_dir / "site" / "styles.css").write_text(
        "*, *::before, *::after { box-sizing: border-box; }\n"
        "body { margin: 0; font-family: sans-serif; overflow-x: hidden; }\n"
        "a:focus-visible { outline: 3px solid #005fcc; outline-offset: 2px; }\n",
        encoding="utf-8",
    )
    (product_dir / "site" / "index.html").write_text(
        "<!DOCTYPE html><html lang='de'><body>TODO_FACTORY_GENERATION</body></html>\n",
        encoding="utf-8",
    )

    (product_dir / "tests" / "test_website_s4.py").write_text(
        "from pathlib import Path\n\n"
        "SITE_DIR = Path(__file__).resolve().parents[1] / 'site'\n\n"
        "def test_content_ac01_ac02_ac03():\n"
        "    html = (SITE_DIR / 'index.html').read_text(encoding='utf-8')\n"
        "    assert 'Nordwerk Industrie-Service' in html\n"
        "    assert 'Praktische Unterstützung für Ihren technischen Betrieb.' in html\n"
        "    assert 'Wartungsplanung' in html\n"
        "    assert 'Ersatzteilkoordination' in html\n"
        "    assert 'Betriebsdokumentation' in html\n"
        "    assert 'Kleine Produktionsbetriebe' in html\n"
        "    assert 'Technische Serviceunternehmen' in html\n"
        "    assert 'Ein fester Ansprechpartner, ein gemeinsam vereinbarter Leistungsumfang und nachvollziehbare Ergebnisse.' in html\n\n"
        "def test_contact_and_navigation_ac04_ac05():\n"
        "    html = (SITE_DIR / 'index.html').read_text(encoding='utf-8')\n"
        "    assert 'href=\"mailto:kontakt@nordwerk.example\"' in html\n"
        "    assert 'Anfrage stellen' in html\n"
        "    assert 'Fiktives Unternehmen – Lehrprojekt der HAW Hamburg. Keine realen Angebote oder Kontaktaufnahme.' in html\n"
        "    assert 'href=\"#leistungen\"' in html and 'id=\"leistungen\"' in html\n"
        "    assert 'href=\"#kontakt\"' in html and 'id=\"kontakt\"' in html\n\n"
        "def test_local_assets_and_a11y_ac06_ac07():\n"
        "    html = (SITE_DIR / 'index.html').read_text(encoding='utf-8')\n"
        "    assert '<html lang=\"de\">' in html\n"
        "    assert 'href=\"styles.css\"' in html\n"
        "    assert (SITE_DIR / 'styles.css').is_file()\n",
        encoding="utf-8",
    )
    return product_dir


class FakeS4ArchitectLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "architecture_decisions": [
                        "Deliver full single-page German HTML5 Release Candidate (AC-01..AC-08).",
                        "Include all 3 services (N-03..N-05), target groups (N-06), working approach (N-07), and anchor navigation.",
                    ],
                    "ready_for_implementation": True,
                    "summary": "Planned Session 4 Release Candidate for Nordwerk.",
                }
            )
        )


class FakeS4ValidImplementationLLM:
    def invoke(self, messages):
        payload = {
            **SESSION_04_REQUIRED_CONTENT,
            "summary": "Generated full Nordwerk Session 4 Release Candidate HTML.",
        }
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


class FakeTruncatedOrBrokenJSONLLM:
    """Simulates a truncated LLM response hitting max_tokens or returning invalid JSON."""

    def invoke(self, messages):
        return AIMessage(
            content='{"N-01": "Nordwerk Industrie-Service", "summary": "Truncated before closing brace'
        )


class FakeConnectionErrorLLM:
    """Simulates a provider/network failure during LLM invocation."""

    def invoke(self, messages):
        raise RuntimeError("Ollama connection refused on port 11434")


class FakeWrongContactFaultLLM:
    """Simulates the Session 4 controlled fault: wrong mailto contact address."""

    def invoke(self, messages):
        faulty = dict(SESSION_04_REQUIRED_CONTENT)
        faulty["N-08_href"] = "mailto:falsch@nordwerk.example"
        faulty["summary"] = "Generated candidate with controlled wrong contact address."
        return AIMessage(content=json.dumps(faulty, ensure_ascii=False))


class FakeS4QALLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "summary": "Executed Session 4 product test families.",
                    "pytest_exit_code": 0,
                    "findings": [],
                    "human_approval_required": True,
                }
            )
        )


def test_failed_or_unparseable_llm_call_never_masked_by_default_html(
    tmp_path: Path,
) -> None:
    """Session 3 Feedback Fix #1: Verify empty, truncated, or failed LLM calls never produce fallback HTML."""
    with pytest.raises(ValueError, match="empty or not a JSON object"):
        _render_html_document({})

    with pytest.raises(ValueError, match="no default HTML fallback allowed"):
        _render_html_document({"summary": "Missing all content fields"})

    product_dir = _create_s4_temp_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    # Case 1: Truncated / invalid JSON from implementation LLM
    task_trunc = CustomerDeliveryTask(
        task_id="NW-S4-TRUNCATED",
        workflow_id="WF-S4-TRUNCATED",
        project_id="website-01",
        product_repo_path=str(product_dir),
        product_test_target="tests/test_website_s4.py",
        max_correction_loops=2,
    )
    res_trunc = run_customer_delivery_workflow(
        task_trunc,
        required_content=dict(SESSION_04_REQUIRED_CONTENT),
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeTruncatedOrBrokenJSONLLM(),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
    )
    assert res_trunc.iterations_used == 2
    assert all(step.status == "error" for step in res_trunc.implementation_history)
    assert all(step.written_file is None for step in res_trunc.implementation_history)
    assert res_trunc.final_qa_result is not None
    assert res_trunc.final_qa_result.status == "failed"
    assert res_trunc.human_gate_status == "escalate_to_human"
    # Verify site/index.html was NOT overwritten with default content
    html_on_disk = (product_dir / "site" / "index.html").read_text(encoding="utf-8")
    assert "TODO_FACTORY_GENERATION" in html_on_disk
    assert "Wartungsplanung" not in html_on_disk

    # Case 2: Even if site/index.html on disk already had valid HTML from a prior run,
    # a failed LLM call in a new workflow run must STILL fail QA and block approval!
    valid_html = _render_html_document(SESSION_04_REQUIRED_CONTENT)
    (product_dir / "site" / "index.html").write_text(valid_html, encoding="utf-8")

    task_err = CustomerDeliveryTask(
        task_id="NW-S4-LLM-ERROR",
        workflow_id="WF-S4-LLM-ERROR",
        project_id="website-01",
        product_repo_path=str(product_dir),
        product_test_target="tests/test_website_s4.py",
        max_correction_loops=1,
    )
    res_err = run_customer_delivery_workflow(
        task_err,
        required_content=dict(SESSION_04_REQUIRED_CONTENT),
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeConnectionErrorLLM(),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
    )
    assert res_err.implementation_history[-1].status == "error"
    assert res_err.final_qa_result is not None
    assert res_err.final_qa_result.status == "failed"
    assert res_err.human_gate_status == "escalate_to_human"

    report_path = Path(res_err.run_directory) / "workflow-report.json"
    with pytest.raises(ValueError, match="pending_approval"):
        record_customer_human_review(
            report_path,
            reviewer="saad",
            decision="approved",
            rationale="Must not approve when LLM call failed.",
        )


def test_factory_commit_clean_check_blocks_dirty_runs_and_records_code_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session 3 Feedback Fix #2: Verify dirty Factory tree is blocked when enforced and code hash is recorded."""
    product_dir = _create_s4_temp_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    monkeypatch.setattr(
        "src.agents.customer_delivery_workflow._get_factory_git_state",
        lambda repo_dir=None: (
            "abc1234deadbeef",
            False,
            ["M src/agents/customer_delivery_workflow.py"],
        ),
    )

    task = CustomerDeliveryTask(
        task_id="NW-S4-DIRTY-CHECK",
        workflow_id="WF-S4-DIRTY-CHECK",
        project_id="website-01",
        product_repo_path=str(product_dir),
        product_test_target="tests/test_website_s4.py",
    )

    with pytest.raises(RuntimeError, match="uncommitted changes in workflow code"):
        run_customer_delivery_workflow(
            task,
            required_content=dict(SESSION_04_REQUIRED_CONTENT),
            architect_llm=FakeS4ArchitectLLM(),
            implementation_llm=FakeS4ValidImplementationLLM(),
            qa_llm=FakeS4QALLM(),
            runs_root=runs_dir,
            enforce_clean_factory_commit=True,
        )

    # Simulate clean committed Factory state
    monkeypatch.setattr(
        "src.agents.customer_delivery_workflow._get_factory_git_state",
        lambda repo_dir=None: ("fbase0011223344", True, []),
    )
    res_clean = run_customer_delivery_workflow(
        task,
        required_content=dict(SESSION_04_REQUIRED_CONTENT),
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeS4ValidImplementationLLM(),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
        enforce_clean_factory_commit=True,
    )
    assert res_clean.factory_commit == "fbase0011223344"
    assert res_clean.factory_commit_clean is True
    assert res_clean.factory_dirty_files == []
    assert res_clean.workflow_code_sha256 == _compute_workflow_code_sha256("website-01")
    assert len(res_clean.workflow_code_sha256) == 64


def test_session_04_controlled_fault_blocks_gate_and_corrected_candidate_passes(
    tmp_path: Path,
) -> None:
    """A3, A4, D1: Verify controlled contact fault fails QA & blocks approval, and corrected version passes."""
    product_dir = _create_s4_temp_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    # 1. Negative run with controlled fault (wrong mailto address)
    fault_task = CustomerDeliveryTask(
        task_id="NW-S4-FAULT-01",
        workflow_id="WF-S4-FAULT-01",
        project_id="website-01",
        product_repo_path=str(product_dir),
        product_test_target="tests/test_website_s4.py",
        max_correction_loops=1,
    )
    res_fault = run_customer_delivery_workflow(
        fault_task,
        required_content=dict(SESSION_04_REQUIRED_CONTENT),
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeWrongContactFaultLLM(),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
    )
    assert res_fault.final_qa_result is not None
    assert res_fault.final_qa_result.status == "failed"
    assert res_fault.final_qa_result.pytest_exit_code != 0
    assert res_fault.human_gate_status == "escalate_to_human"

    fault_report = Path(res_fault.run_directory) / "workflow-report.json"
    with pytest.raises(ValueError, match="pending_approval"):
        record_customer_human_review(
            fault_report,
            reviewer="felix",
            decision="approved",
            rationale="Cannot approve broken contact link.",
        )

    # Reviewer records explicit rejection (changes_requested) on the fault run
    fault_review_path = record_customer_human_review(
        fault_report,
        reviewer="felix",
        decision="changes_requested",
        rationale="Controlled fault detected: mailto:falsch@nordwerk.example failed AC-04 check.",
    )
    fault_review = json.loads(fault_review_path.read_text(encoding="utf-8"))
    assert fault_review["decision"] == "changes_requested"

    # 2. Corrected Release Candidate run passes all 3 check families and is approved
    rc_task = CustomerDeliveryTask(
        task_id="NW-S4-001",
        workflow_id="WF-S4-RC-01",
        project_id="website-01",
        product_repo_path=str(product_dir),
        product_test_target="tests/test_website_s4.py",
        max_correction_loops=2,
    )
    res_rc = run_customer_delivery_workflow(
        rc_task,
        required_content=dict(SESSION_04_REQUIRED_CONTENT),
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeS4ValidImplementationLLM(),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
    )
    assert res_rc.final_qa_result is not None
    assert res_rc.final_qa_result.status == "passed"
    assert res_rc.final_qa_result.pytest_exit_code == 0
    assert res_rc.human_gate_status == "pending_approval"

    rc_report = Path(res_rc.run_directory) / "workflow-report.json"
    rc_review_path = record_customer_human_review(
        rc_report,
        reviewer="saad",
        decision="approved",
        rationale="Release Candidate passes all 3 automated check families (AC-01..AC-08) and browser review.",
    )
    rc_review = json.loads(rc_review_path.read_text(encoding="utf-8"))
    assert rc_review["decision"] == "approved"


def test_r01_baseline_task_configuration_and_4_service_rendering() -> None:
    """C1, L4.4: Verify R-01 task configuration adds the 4th service card ('Projektkoordination') cleanly."""
    task, req_content = build_task_from_project_config("website-01", task_id="R-01")
    assert task.task_id == "R-01"
    assert req_content["R-01_title"] == "Projektkoordination"
    assert (
        req_content["R-01_text"]
        == "Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team."
    )

    html = _render_html_document(req_content)
    assert "Wartungsplanung" in html
    assert "Ersatzteilkoordination" in html
    assert "Betriebsdokumentation" in html
    assert "Projektkoordination" in html
    assert (
        "Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team."
        in html
    )
    assert html.count('<article class="service-card">') == 4
