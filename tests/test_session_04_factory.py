"""Session 4 Factory unit tests:
- Reuse of central Factory configuration across NW-S4-001 and R-01 (A1, L4.1)
- Strict LLM output validation: failed/unparseable/incomplete LLM output is never
  masked by silent default HTML (Session 3 Feedback remediation, A4)
- Controlled fault detection, gate blocking (escalate_to_human / changes_requested),
  and subsequent correction passing the gate (A3, A4, L4.2, L4.3)
- Reference task R-01 ("Projektkoordination") preservation of AC-01..AC-08 (C1, L4.4)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_delivery_workflow import (
    DEFAULT_S4_REQUIRED_CONTENT,
    _render_html_document,
    build_task_from_project_config,
    record_customer_human_review,
    run_customer_delivery_workflow,
)

S4_PRODUCT_TEST_CODE = '''from html.parser import HTMLParser
from pathlib import Path
import unittest

SITE_DIR = Path(__file__).resolve().parents[1] / "site"
INDEX_HTML = SITE_DIR / "index.html"
STYLES_CSS = SITE_DIR / "styles.css"

class _S4Inspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_lang = None
        self.ids: set[str] = set()
        self.links: list[tuple[str, str]] = []
        self.nav_links: list[tuple[str, str]] = []
        self.stylesheets: list[str] = []
        self.in_nav = False
        self._href = None
        self._link_text: list[str] = []
        self.text_chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        amap = dict(attrs)
        if amap.get("id"):
            self.ids.add(amap["id"])
        if tag == "html" and self.html_lang is None:
            self.html_lang = amap.get("lang")
        if tag == "nav":
            self.in_nav = True
        if tag == "link" and amap.get("rel") == "stylesheet" and amap.get("href"):
            self.stylesheets.append(amap["href"])
        if tag == "a":
            self._href = amap.get("href") or ""
            self._link_text = []

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_nav = False
        if tag == "a" and self._href is not None:
            label = " ".join("".join(self._link_text).split())
            self.links.append((self._href, label))
            if self.in_nav:
                self.nav_links.append((self._href, label))
            self._href = None
            self._link_text = []

    def handle_data(self, data):
        cleaned = " ".join(data.split())
        if cleaned:
            self.text_chunks.append(cleaned)
        if self._href is not None:
            self._link_text.append(data)

class TestWebsiteS4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = INDEX_HTML.read_text(encoding="utf-8")
        cls.inspector = _S4Inspector()
        cls.inspector.feed(cls.raw)
        cls.text = " ".join(cls.inspector.text_chunks)

    def test_family1_required_content_ac01_ac02_ac03(self):
        self.assertNotIn("TODO_FACTORY_GENERATION", self.raw)
        for required_str in [
            "Nordwerk Industrie-Service",
            "Praktische Unterstützung für Ihren technischen Betrieb.",
            "Wartungsplanung",
            "Wir strukturieren Wartungsaufgaben und dokumentieren Zuständigkeiten für kleine technische Betriebe.",
            "Ersatzteilkoordination",
            "Wir unterstützen bei der Abstimmung von Ersatzteilbedarfen und Lieferterminen.",
            "Betriebsdokumentation",
            "Wir bringen technische Unterlagen in eine nachvollziehbare und nutzbare Struktur.",
            "Kleine Produktionsbetriebe",
            "Technische Serviceunternehmen",
            "Ein fester Ansprechpartner, ein gemeinsam vereinbarter Leistungsumfang und nachvollziehbare Ergebnisse.",
            "Fiktives Unternehmen – Lehrprojekt der HAW Hamburg. Keine realen Angebote oder Kontaktaufnahme.",
        ]:
            self.assertIn(required_str, self.text)

    def test_family2_contact_and_navigation_targets_ac04_ac05(self):
        self.assertIn(("mailto:kontakt@nordwerk.example", "Anfrage stellen"), self.inspector.links)
        nav_hrefs = [href for href, _ in self.inspector.nav_links]
        self.assertIn("#leistungen", nav_hrefs)
        self.assertIn("#kontakt", nav_hrefs)
        for href, _ in self.inspector.links:
            if href.startswith("#"):
                target_id = href[1:]
                self.assertIn(target_id, self.inspector.ids, f"Broken internal anchor link: {href}")

    def test_family3_local_assets_and_usability_ac05_ac06_ac07(self):
        self.assertEqual(self.inspector.html_lang, "de")
        self.assertTrue(len(self.inspector.stylesheets) >= 1)
        for css_ref in self.inspector.stylesheets:
            self.assertFalse(css_ref.startswith("http"), f"External asset forbidden: {css_ref}")
            self.assertTrue((SITE_DIR / css_ref).is_file(), f"Missing local asset: {css_ref}")
'''


def _create_s4_temp_product_checkout(tmp_path: Path) -> Path:
    """Create an isolated customer product checkout with S4 issue, CSS, and 3 check families."""
    product_dir = tmp_path / "client-01-website"
    (product_dir / "docs").mkdir(parents=True, exist_ok=True)
    (product_dir / "site").mkdir(parents=True, exist_ok=True)
    (product_dir / "tests").mkdir(parents=True, exist_ok=True)

    (product_dir / "docs" / "issue-02-session-04.md").write_text(
        "# Issue #2: [NW-S4-001] Nordwerk Session 4 Release Candidate (AC-01..AC-08)\n",
        encoding="utf-8",
    )
    (product_dir / "site" / "styles.css").write_text(
        "body { font-family: sans-serif; }\n"
        "a:focus-visible { outline: 3px solid #1d4ed8; }\n"
        "@media (max-width: 600px) { .container { padding: 1rem; } }\n",
        encoding="utf-8",
    )
    (product_dir / "site" / "index.html").write_text(
        "<!DOCTYPE html><html lang='de'><body>TODO_FACTORY_GENERATION</body></html>\n",
        encoding="utf-8",
    )
    (product_dir / "tests" / "test_website_s4.py").write_text(
        S4_PRODUCT_TEST_CODE,
        encoding="utf-8",
    )
    return product_dir


class FakeS4ArchitectLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "summary": "Planned Session 4 Release Candidate HTML5 structure for AC-01..AC-08.",
                    "architecture_decisions": [
                        "Include header nav with internal anchors (#leistungen, #zielgruppen, #arbeitsweise, #kontakt).",
                        "Include all 3 services (N-03, N-04, N-05), target groups (N-06), and working approach (N-07).",
                        "Maintain mailto:kontakt@nordwerk.example CTA and HAW course notice.",
                    ],
                    "ready_for_implementation": True,
                }
            )
        )


class FakeS4ValidImplementationLLM:
    """Returns valid JSON built from the required_content passed in the prompt."""

    def __init__(self, extra_overrides: dict[str, str] | None = None) -> None:
        self.extra_overrides = extra_overrides or {}

    def invoke(self, messages):
        payload = {"summary": "Generated complete Nordwerk S4 HTML from handover contract."}
        payload.update(DEFAULT_S4_REQUIRED_CONTENT)
        # If R-01 is in the prompt, include R-01 fields as well
        human_content = str(messages[-1].content)
        if "R-01_title" in human_content:
            payload["R-01_title"] = "Projektkoordination"
            payload["R-01_text"] = (
                "Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team."
            )
        payload.update(self.extra_overrides)
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


class FakeFailingExceptionLLM:
    """Simulates a runtime/timeout error from the LLM provider."""

    def invoke(self, messages):
        raise RuntimeError("Simulated Ollama connection timeout")


class FakeTruncatedJSONLLM:
    """Simulates a truncated non-parseable JSON output (hitting max_tokens ceiling)."""

    def invoke(self, messages):
        return AIMessage(
            content='{"summary": "Truncated output before closing brace", "N-01": "Nordwerk'
        )


class FakeIncompleteFieldsLLM:
    """Simulates valid JSON that omits required content fields (e.g. only summary)."""

    def invoke(self, messages):
        return AIMessage(content=json.dumps({"summary": "Omitted all N-01..N-09 keys"}))


class FakeS4QALLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "summary": "Executed 3 automated product check families in test_website_s4.py.",
                    "pytest_exit_code": 0,
                    "findings": [],
                    "human_approval_required": True,
                }
            )
        )


def test_s4_configuration_and_task_reuse() -> None:
    """A1 / L4.1: Verify website-01.yaml supports NW-S3-001, NW-S4-001, and R-01 without copying agents."""
    task_s4, req_s4 = build_task_from_project_config("website-01", task_id="NW-S4-001")
    assert task_s4.task_id == "NW-S4-001"
    assert task_s4.product_test_target == "tests/test_website_s4.py"
    assert "AC-08" in task_s4.acceptance_criteria
    assert req_s4["N-04_title"] == "Ersatzteilkoordination"
    assert req_s4["N-05_title"] == "Betriebsdokumentation"
    assert req_s4["N-06_target_1"] == "Kleine Produktionsbetriebe"
    assert req_s4["N-06_target_2"] == "Technische Serviceunternehmen"
    assert "fester Ansprechpartner" in req_s4["N-07"]

    task_r01, req_r01 = build_task_from_project_config("website-01", task_id="R-01")
    assert task_r01.task_id == "R-01"
    assert "R-01" in task_r01.acceptance_criteria
    assert req_r01["R-01_title"] == "Projektkoordination"
    assert (
        req_r01["R-01_text"]
        == "Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team."
    )


def test_failed_or_unparseable_llm_never_masked_by_default_html(tmp_path: Path) -> None:
    """Session 3 Feedback Fix + A4: Failed, truncated, or incomplete LLM responses must NEVER
    fall back to default HTML or reach pending_approval.
    """
    # 1. Unit-level check on _render_html_document
    with pytest.raises(ValueError, match="empty"):
        _render_html_document({})

    with pytest.raises(ValueError, match="missing required"):
        _render_html_document(
            {"summary": "Missing keys", "N-01": "Nordwerk Industrie-Service"},
            required_content=DEFAULT_S4_REQUIRED_CONTENT,
        )

    # 2. Workflow-level check: LLM exception, truncated JSON, and incomplete JSON
    for label, bad_llm in [
        ("exception", FakeFailingExceptionLLM()),
        ("truncated_json", FakeTruncatedJSONLLM()),
        ("incomplete_fields", FakeIncompleteFieldsLLM()),
    ]:
        product_dir = _create_s4_temp_product_checkout(tmp_path / label)
        runs_dir = tmp_path / label / "runs"
        task, _ = build_task_from_project_config(
            "website-01",
            product_repo_path=str(product_dir),
            task_id="NW-S4-001",
            workflow_id=f"WF-S4-BAD-LLM-{label.upper()}",
            max_correction_loops=2,
        )
        res = run_customer_delivery_workflow(
            task,
            architect_llm=FakeS4ArchitectLLM(),
            implementation_llm=bad_llm,
            qa_llm=FakeS4QALLM(),
            runs_root=runs_dir,
        )

        # Must fail implementation, must NOT overwrite index.html with valid default HTML,
        # and must escalate to human rather than pending_approval.
        assert res.iterations_used == 2
        assert all(imp.status == "error" for imp in res.implementation_history)
        assert all(imp.written_file is None for imp in res.implementation_history)
        assert all(q.status == "failed" for q in res.qa_history)
        assert res.human_gate_status == "escalate_to_human"

        # Original placeholder in index.html was never masked by silent default HTML
        html_on_disk = (product_dir / "site" / "index.html").read_text(encoding="utf-8")
        assert "TODO_FACTORY_GENERATION" in html_on_disk

        report_path = Path(res.run_directory) / "workflow-report.json"
        with pytest.raises(ValueError, match="pending_approval"):
            record_customer_human_review(
                report_path,
                reviewer="saad",
                decision="approved",
                rationale="Must not approve when LLM failed.",
            )


def test_controlled_fault_detected_blocked_and_corrected(tmp_path: Path) -> None:
    """A3, A4, L4.2, L4.3: Introduce a controlled contact/link fault in an isolated test copy,
    verify that the product check fails and the gate blocks approval, then correct the fault
    and verify that the candidate passes and can be approved.
    """
    product_dir = _create_s4_temp_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    # Step 1: Controlled Fault Run (incorrect contact email address)
    fault_task, _ = build_task_from_project_config(
        "website-01",
        product_repo_path=str(product_dir),
        task_id="NW-S4-001",
        workflow_id="WF-S4-CONTROLLED-FAULT",
        max_correction_loops=1,
    )
    fault_res = run_customer_delivery_workflow(
        fault_task,
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeS4ValidImplementationLLM(
            extra_overrides={"N-08_href": "mailto:falsch@nordwerk.example"}
        ),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
    )

    assert fault_res.final_qa_result is not None
    assert fault_res.final_qa_result.status == "failed"
    assert fault_res.final_qa_result.pytest_exit_code != 0
    assert fault_res.human_gate_status == "escalate_to_human"

    fault_manifest = json.loads(Path(fault_res.manifest_file).read_text(encoding="utf-8"))
    assert fault_manifest["product_test_passed"] is False

    fault_report = Path(fault_res.run_directory) / "workflow-report.json"
    with pytest.raises(ValueError, match="pending_approval"):
        record_customer_human_review(
            fault_report,
            reviewer="felix",
            decision="approved",
            rationale="Attempt to approve faulty contact address must be blocked.",
        )

    # Record explicit rejection (changes_requested) on the faulty run
    fault_review_path = record_customer_human_review(
        fault_report,
        reviewer="felix",
        decision="changes_requested",
        rationale="Blocked by quality gate: contact href was mailto:falsch@nordwerk.example instead of mailto:kontakt@nordwerk.example.",
    )
    fault_review = json.loads(fault_review_path.read_text(encoding="utf-8"))
    assert fault_review["decision"] == "changes_requested"

    # Step 2: Corrected Run on the same checkout -> passes all 3 check families
    fixed_task, _ = build_task_from_project_config(
        "website-01",
        product_repo_path=str(product_dir),
        task_id="NW-S4-001",
        workflow_id="WF-S4-CORRECTED-CANDIDATE",
        max_correction_loops=2,
    )
    fixed_res = run_customer_delivery_workflow(
        fixed_task,
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeS4ValidImplementationLLM(),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
    )

    assert fixed_res.final_qa_result is not None
    assert fixed_res.final_qa_result.status == "passed"
    assert fixed_res.final_qa_result.pytest_exit_code == 0
    assert fixed_res.human_gate_status == "pending_approval"

    fixed_report = Path(fixed_res.run_directory) / "workflow-report.json"
    approved_review_path = record_customer_human_review(
        fixed_report,
        reviewer="saad",
        decision="approved",
        rationale="All 3 automated product check families passed; contact address corrected to mailto:kontakt@nordwerk.example.",
    )
    approved_review = json.loads(approved_review_path.read_text(encoding="utf-8"))
    assert approved_review["decision"] == "approved"
    assert "AC-08" in approved_review["accepted_criteria"]


def test_r01_baseline_task_renders_projektkoordination_and_preserves_s4_content(
    tmp_path: Path,
) -> None:
    """C1, L4.4: Verify R-01 reference task adds 'Projektkoordination' card while passing all S4 checks."""
    product_dir = _create_s4_temp_product_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    r01_task, _ = build_task_from_project_config(
        "website-01",
        product_repo_path=str(product_dir),
        task_id="R-01",
        workflow_id="WF-R01-TEST-001",
        max_correction_loops=2,
    )
    res = run_customer_delivery_workflow(
        r01_task,
        architect_llm=FakeS4ArchitectLLM(),
        implementation_llm=FakeS4ValidImplementationLLM(),
        qa_llm=FakeS4QALLM(),
        runs_root=runs_dir,
    )

    assert res.human_gate_status == "pending_approval"
    assert res.final_qa_result is not None
    assert res.final_qa_result.status == "passed"

    rendered_html = (product_dir / "site" / "index.html").read_text(encoding="utf-8")
    assert "Projektkoordination" in rendered_html
    assert (
        "Wir koordinieren klar abgegrenzte technische Vorhaben mit Ihrem Team."
        in rendered_html
    )
    # Previous 3 services, target groups, working approach, and mailto link remain intact
    assert "Wartungsplanung" in rendered_html
    assert "Ersatzteilkoordination" in rendered_html
    assert "Betriebsdokumentation" in rendered_html
    assert "mailto:kontakt@nordwerk.example" in rendered_html
