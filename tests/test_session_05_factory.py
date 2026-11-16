"""Session 5 Factory unit tests verifying:
1. F-NEW Improvement #1 (C1, L5.2): Delta-key extraction from verified R-BASE HTML and delta-prompt merging
   for R-01 and NW-S5-CR01 without any silent fallback when delta keys are missing.
2. F-NEW Improvement #2 (A4, C1, L5.2): Deterministic in-memory pre-gate validator catching missing verbatim
   strings, broken #anchor targets, <form> elements, and forbidden claims before QA handover.
3. Session 5 Customer Change CR-01 (A2, B1..B3, L5.1): End-to-end delivery of German target group
   'Technische Einkaufsabteilungen' + standalone English entry page 'site/en.html' + '#en' overview
   with AC-01..AC-08 regression checks and human gate review.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_delivery_workflow import (
    SESSION_04_REQUIRED_CONTENT,
    SESSION_05_CR01_DELTA_CONTENT,
    SESSION_05_CR01_REQUIRED_CONTENT,
    _render_english_html_document,
    _render_html_document,
    build_task_from_project_config,
    extract_verified_baseline_from_product_html,
    record_customer_human_review,
    run_customer_delivery_workflow,
    validate_rendered_html_pre_gate,
)
from src.agents.task_models import CustomerDeliveryTask


def _create_s5_rbase_product_checkout(tmp_path: Path) -> Path:
    """Create a temporary customer product checkout pre-populated with the verified R-BASE (ecb5981) HTML."""
    product_dir = tmp_path / "client-01-website"
    (product_dir / "docs").mkdir(parents=True, exist_ok=True)
    (product_dir / "site").mkdir(parents=True, exist_ok=True)
    (product_dir / "tests").mkdir(parents=True, exist_ok=True)

    (product_dir / "docs" / "issue-02-session-04.md").write_text(
        "# Issue #2: [NW-S4-001] Nordwerk Session 4 Release Candidate\n",
        encoding="utf-8",
    )
    (product_dir / "docs" / "issue-03-session-05-cr01.md").write_text(
        "# Issue #3: [NW-S5-CR01] Customer Change CR-01 (English Entry View & Technical Purchasing)\n",
        encoding="utf-8",
    )
    (product_dir / "site" / "styles.css").write_text(
        "*, *::before, *::after { box-sizing: border-box; }\n"
        "body { margin: 0; font-family: sans-serif; overflow-x: hidden; }\n"
        "a:focus-visible { outline: 3px solid #005fcc; outline-offset: 2px; }\n",
        encoding="utf-8",
    )
    rbase_html = _render_html_document(SESSION_04_REQUIRED_CONTENT)
    (product_dir / "site" / "index.html").write_text(rbase_html, encoding="utf-8")

    (product_dir / "tests" / "verify_r01_baseline.py").write_text(
        "from pathlib import Path\n\n"
        "def test_r01_service_card():\n"
        "    html = (Path(__file__).resolve().parents[1] / 'site' / 'index.html').read_text(encoding='utf-8')\n"
        "    assert 'Projektkoordination' in html\n"
        "    assert 'Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team.' in html\n"
        "    assert html.count('<article class=\"service-card\">') == 4\n",
        encoding="utf-8",
    )

    (product_dir / "tests" / "test_website_s5.py").write_text(
        "from pathlib import Path\n\n"
        "SITE_DIR = Path(__file__).resolve().parents[1] / 'site'\n\n"
        "def test_cr01_german_and_english_views():\n"
        "    de_html = (SITE_DIR / 'index.html').read_text(encoding='utf-8')\n"
        "    assert '<html lang=\"de\">' in de_html\n"
        "    assert 'Kleine Produktionsbetriebe' in de_html\n"
        "    assert 'Technische Serviceunternehmen' in de_html\n"
        "    assert 'Technische Einkaufsabteilungen' in de_html\n"
        "    assert 'href=\"en.html\"' in de_html\n"
        "    en_path = SITE_DIR / 'en.html'\n"
        "    assert en_path.is_file()\n"
        "    en_html = en_path.read_text(encoding='utf-8')\n"
        "    assert '<html lang=\"en\">' in en_html\n"
        "    assert '<title>' in en_html\n"
        "    assert 'Nordwerk Industrie-Service' in en_html\n"
        "    assert 'Practical support for your technical operations.' in en_html\n"
        "    assert 'Maintenance planning' in en_html\n"
        "    assert 'Spare parts coordination' in en_html\n"
        "    assert 'Operational documentation' in en_html\n"
        "    assert 'Technical purchasing departments' in en_html\n"
        "    assert 'Request information' in en_html\n"
        "    assert 'mailto:kontakt@nordwerk.example' in en_html\n"
        "    assert 'Fictional company – HAW Hamburg course project. No real offers or contact.' in en_html\n"
        "    assert 'href=\"index.html\"' in en_html\n",
        encoding="utf-8",
    )
    return product_dir


class FakeS5ArchitectLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "architecture_decisions": [
                        "Reuse verified R-BASE German content via delta-key merging.",
                        "Render German target group expansion and English entry page (site/en.html + #en).",
                    ],
                    "ready_for_implementation": True,
                    "summary": "Planned F-NEW delta handover for Nordwerk change task.",
                }
            )
        )


class FakeR01DeltaOnlyLLM:
    """Emits ONLY the 2 R-01 delta keys + summary (testing F-NEW delta prompt & merge)."""

    def __init__(self) -> None:
        self.last_human_prompt = ""

    def invoke(self, messages):
        self.last_human_prompt = str(messages[-1].content)
        return AIMessage(
            content=json.dumps(
                {
                    "R-01_title": "Projektkoordination",
                    "R-01_text": "Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team.",
                    "summary": "Added 4th service card Projektkoordination via F-NEW delta merge.",
                },
                ensure_ascii=False,
            )
        )


class FakeCR01DeltaOnlyLLM:
    """Emits ONLY the 10 CR-01 delta keys + summary (testing F-NEW delta merge for CR-01)."""

    def invoke(self, messages):
        payload = {
            **SESSION_05_CR01_DELTA_CONTENT,
            "summary": "Added Technische Einkaufsabteilungen and English view (site/en.html).",
        }
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


class FakeMissingDeltaKeyLLM:
    """Omits EN_target_group to verify delta mode never falls back to default strings."""

    def invoke(self, messages):
        incomplete = dict(SESSION_05_CR01_DELTA_CONTENT)
        incomplete.pop("EN_target_group")
        incomplete["summary"] = "Incomplete CR-01 delta output."
        return AIMessage(content=json.dumps(incomplete, ensure_ascii=False))


class FakeS5QALLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "summary": "Verified Session 5 product test suite and regression checks.",
                    "pytest_exit_code": 0,
                    "findings": [],
                    "human_approval_required": True,
                }
            )
        )


def test_fnew_delta_key_extraction_and_r01_delta_merge(tmp_path: Path) -> None:
    """C1, L5.2: Verify F-NEW extracts verified R-BASE baseline and prompts/merges only R-01 delta keys."""
    assert extract_verified_baseline_from_product_html("<html>TODO_FACTORY_GENERATION</html>") == {}
    rbase_html = _render_html_document(SESSION_04_REQUIRED_CONTENT)
    extracted = extract_verified_baseline_from_product_html(rbase_html)
    assert extracted == SESSION_04_REQUIRED_CONTENT

    product_dir = _create_s5_rbase_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    task, req_content = build_task_from_project_config(
        "website-01",
        product_repo_path=str(product_dir),
        task_id="R-01",
        workflow_id="R-01-FNEW-UNIT",
    )
    delta_llm = FakeR01DeltaOnlyLLM()
    res = run_customer_delivery_workflow(
        task,
        required_content=req_content,
        architect_llm=FakeS5ArchitectLLM(),
        implementation_llm=delta_llm,
        qa_llm=FakeS5QALLM(),
        runs_root=runs_dir,
    )

    assert res.architect_result.handover.delta_keys == ["R-01_title", "R-01_text"]
    assert res.architect_result.handover.baseline_content == SESSION_04_REQUIRED_CONTENT
    # Verify the implementation prompt only requested the 2 delta keys + summary
    assert '"R-01_title"' in delta_llm.last_human_prompt
    assert '"N-03_text"' not in delta_llm.last_human_prompt

    assert res.iterations_used == 1
    assert res.implementation_history[-1].status == "completed"
    assert res.implementation_history[-1].handover.pre_gate_validation_passed is True
    assert res.final_qa_result is not None
    assert res.final_qa_result.status == "passed"
    assert res.human_gate_status == "pending_approval"


def test_fnew_deterministic_pre_gate_validator_catches_faults() -> None:
    """A4, C1: Verify validate_rendered_html_pre_gate catches missing strings, broken anchors, and forms."""
    valid_de = _render_html_document(SESSION_05_CR01_REQUIRED_CONTENT)
    valid_en = _render_english_html_document(SESSION_05_CR01_REQUIRED_CONTENT)
    assert (
        validate_rendered_html_pre_gate(
            valid_de, SESSION_05_CR01_REQUIRED_CONTENT, en_html=valid_en
        )
        == []
    )

    # 1. Broken internal anchor link
    broken_anchor_html = valid_de.replace('href="#kontakt"', 'href="#nicht-vorhanden"')
    findings_anchor = validate_rendered_html_pre_gate(
        broken_anchor_html, SESSION_04_REQUIRED_CONTENT
    )
    assert any("Broken internal anchor href='#nicht-vorhanden'" in f for f in findings_anchor)

    # 2. Forbidden <form> or unverified claim
    forbidden_html = valid_de + "\n<form action='/send'></form><p>ISO 9001 certified</p>"
    findings_forbidden = validate_rendered_html_pre_gate(
        forbidden_html, SESSION_04_REQUIRED_CONTENT
    )
    assert any("Forbidden <form>" in f for f in findings_forbidden)
    assert any("ISO 9001" in f for f in findings_forbidden)


def test_session_05_cr01_bilingual_delivery_and_missing_delta_rejection(
    tmp_path: Path,
) -> None:
    """A2, B1..B3, L5.1: Verify CR-01 writes both site/index.html and site/en.html, and rejects missing delta keys."""
    product_dir = _create_s5_rbase_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    # 1. Missing delta key must fail validation without silent fallback
    bad_task = CustomerDeliveryTask(
        task_id="NW-S5-CR01-MISSING",
        workflow_id="WF-S5-CR01-MISSING",
        project_id="website-01",
        product_repo_path=str(product_dir),
        input_files=["docs/issue-03-session-05-cr01.md", "site/index.html"],
        product_test_target="tests/test_website_s5.py",
        max_correction_loops=1,
    )
    res_bad = run_customer_delivery_workflow(
        bad_task,
        required_content=dict(SESSION_05_CR01_REQUIRED_CONTENT),
        architect_llm=FakeS5ArchitectLLM(),
        implementation_llm=FakeMissingDeltaKeyLLM(),
        qa_llm=FakeS5QALLM(),
        runs_root=runs_dir,
    )
    assert res_bad.implementation_history[-1].status == "error"
    assert "missing required delta keys" in res_bad.implementation_history[-1].summary
    assert res_bad.human_gate_status == "escalate_to_human"

    # 2. Complete CR-01 delta run generates both site/index.html and site/en.html and passes QA
    cr01_task, cr01_req = build_task_from_project_config(
        "website-01",
        product_repo_path=str(product_dir),
        task_id="NW-S5-CR01",
        workflow_id="WF-S5-CR01-OK",
    )
    res_ok = run_customer_delivery_workflow(
        cr01_task,
        required_content=cr01_req,
        architect_llm=FakeS5ArchitectLLM(),
        implementation_llm=FakeCR01DeltaOnlyLLM(),
        qa_llm=FakeS5QALLM(),
        runs_root=runs_dir,
    )
    assert res_ok.iterations_used == 1
    imp = res_ok.implementation_history[-1]
    assert imp.status == "completed"
    assert imp.handover.modified_files == ["site/index.html", "site/en.html"]
    assert imp.handover.pre_gate_validation_passed is True
    assert res_ok.final_qa_result is not None
    assert res_ok.final_qa_result.status == "passed"
    assert res_ok.human_gate_status == "pending_approval"

    report_path = Path(res_ok.run_directory) / "workflow-report.json"
    rev_path = record_customer_human_review(
        report_path,
        reviewer="saad",
        decision="approved",
        tested_source_commit="99887766554433221100aabbccddeeff00112233",
        rationale="Technical release approval for CR-01 (site/index.html + site/en.html); customer acceptance pending live review.",
    )
    rev_data = json.loads(rev_path.read_text(encoding="utf-8"))
    assert rev_data["decision"] == "approved"
    assert "site/index.html" in rev_data["reviewed_artifact_hashes"]
    assert "site/en.html" in rev_data["reviewed_artifact_hashes"]
    assert any("pending_customer_acceptance" in c for c in rev_data["open_criteria"])
