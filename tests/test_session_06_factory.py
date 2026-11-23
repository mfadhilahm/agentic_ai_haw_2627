"""Session 6 Factory unit tests verifying:
1. Project switching & Factory reuse (A1, L6.1): quotation-02 loads cleanly alongside website-01
   with distinct customer repo paths, write prefixes, and product check targets.
2. Deterministic project isolation (A4, L6.1): executing a HansePack quotation-02 workflow run
   never modifies any Nordwerk (client-01-website) file, and sandbox rejects cross-repo / out-of-prefix writes.
3. Multi-agent cooperation & real product test integration (A2, A3, B1..B4, L6.2):
   Architect -> Implementation -> QA structured handovers deliver quotation/calculator.py passing
   Q01, Q03, and E01 checks and support explicit human gate review.
4. Strict no-fallback validation (A4): missing or invalid LLM rule output never falls back to default
   product code, leaves the placeholder intact, and escalates to human review.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_delivery_workflow import (
    HANSEPACK_S6_REQUIRED_RULES,
    SESSION_05_CR01_REQUIRED_CONTENT,
    _render_english_html_document,
    _render_html_document,
    build_task_from_project_config,
    load_project_config,
    record_customer_human_review,
    render_python_module_from_contract,
    run_customer_delivery_workflow,
    run_product_test_tool,
    validate_and_normalize_python_contract_fields,
    validate_product_workspace_path,
    validate_python_module_pre_gate,
    validate_rendered_html_pre_gate,
    write_product_file_tool,
)
from src.agents.task_models import (
    CustomerDeliveryTask,
    ProductHandoverPayload,
    QAHandoverPayload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _snapshot_tree_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def _create_s6_temp_nordwerk_checkout(tmp_path: Path) -> Path:
    """Create an isolated temporary Nordwerk checkout matching the final Session 5 release (84d5baf / v1.0.0-s5-rc),
    including both the German page (site/index.html) and the English website (site/en.html).
    """
    nordwerk_dir = tmp_path / "client-01-website"
    (nordwerk_dir / "docs").mkdir(parents=True, exist_ok=True)
    (nordwerk_dir / "site").mkdir(parents=True, exist_ok=True)
    (nordwerk_dir / "tests").mkdir(parents=True, exist_ok=True)

    de_html = _render_html_document(SESSION_05_CR01_REQUIRED_CONTENT)
    en_html = _render_english_html_document(SESSION_05_CR01_REQUIRED_CONTENT)

    (nordwerk_dir / "site" / "index.html").write_text(de_html, encoding="utf-8")
    (nordwerk_dir / "site" / "en.html").write_text(en_html, encoding="utf-8")
    (nordwerk_dir / "site" / "styles.css").write_text(
        "*, *::before, *::after { box-sizing: border-box; }\n"
        "body { margin: 0; font-family: sans-serif; overflow-x: hidden; }\n"
        "a:focus-visible { outline: 3px solid #005fcc; outline-offset: 2px; }\n"
        "@media (min-width: 768px) { .service-grid { display: grid; } }\n",
        encoding="utf-8",
    )
    (nordwerk_dir / "docs" / "issue-03-session-05-cr01.md").write_text(
        "# Issue #3: [NW-S5-CR01] Nordwerk Session 5 Bilingual Release (84d5baf)\n",
        encoding="utf-8",
    )
    (nordwerk_dir / "docs" / "security-advisory-sr01.md").write_text(
        "# SR-01 Security Advisory & Component Inventory (84d5baf)\n",
        encoding="utf-8",
    )
    (nordwerk_dir / "docs" / "release-s5-handover.md").write_text(
        "# Session 5 Final Release Handover (84d5baf / v1.0.0-s5-rc)\n",
        encoding="utf-8",
    )
    (nordwerk_dir / "tests" / "test_website_s5.py").write_text(
        "from pathlib import Path\n\n"
        "SITE_DIR = Path(__file__).resolve().parents[1] / 'site'\n\n"
        "def test_s5_final_release_84d5baf_german_and_english_pages():\n"
        "    de_html = (SITE_DIR / 'index.html').read_text(encoding='utf-8')\n"
        "    en_html = (SITE_DIR / 'en.html').read_text(encoding='utf-8')\n"
        "    assert '<html lang=\"de\">' in de_html\n"
        "    assert 'Technische Einkaufsabteilungen' in de_html\n"
        "    assert 'href=\"en.html\"' in de_html\n"
        "    assert '<html lang=\"en\">' in en_html\n"
        "    assert 'Practical support for your technical operations.' in en_html\n"
        "    assert 'Technical purchasing departments' in en_html\n"
        "    assert 'Request information' in en_html\n"
        "    assert 'href=\"index.html\"' in en_html\n",
        encoding="utf-8",
    )
    return nordwerk_dir


def _create_s6_temp_hansepack_checkout(tmp_path: Path) -> Path:
    """Create an isolated temporary HansePack checkout with unchanged customer fixtures."""
    product_dir = tmp_path / "client-02-quotation"
    (product_dir / "data").mkdir(parents=True, exist_ok=True)
    (product_dir / "docs").mkdir(parents=True, exist_ok=True)
    (product_dir / "quotation").mkdir(parents=True, exist_ok=True)
    (product_dir / "tests").mkdir(parents=True, exist_ok=True)

    # Copy binding customer fixtures from the task sheets directory in REPO_ROOT
    task_fixtures_dir = REPO_ROOT / "task sheets" / "session-06-08"
    shutil.copyfile(
        task_fixtures_dir / "HansePack_Katalog.json",
        product_dir / "data" / "HansePack_Katalog.json",
    )
    shutil.copyfile(
        task_fixtures_dir / "HansePack_Referenzfaelle.json",
        product_dir / "data" / "HansePack_Referenzfaelle.json",
    )

    (product_dir / "docs" / "issue-01-session-06.md").write_text(
        "# Issue #1: [HP-S6-001] HansePack Session 6 Quotation Slice\n"
        "Scope: HP-AC01, HP-AC02 (Q01, Q03), HP-AC04 (E01).\n",
        encoding="utf-8",
    )
    (product_dir / "quotation" / "__init__.py").write_text(
        "from quotation.calculator import QuotationValidationError, calculate_quotation, load_catalogue\n",
        encoding="utf-8",
    )
    (product_dir / "quotation" / "calculator.py").write_text(
        '"""TODO_FACTORY_GENERATION"""\n\n'
        "class QuotationValidationError(ValueError):\n"
        "    def __init__(self, message: str, reason: str = 'validation_error') -> None:\n"
        "        super().__init__(message)\n"
        "        self.reason = reason\n\n"
        "def load_catalogue(catalogue_path=None):\n"
        "    raise NotImplementedError('TODO_FACTORY_GENERATION')\n\n"
        "def calculate_quotation(items, *, catalogue_path=None, rule_version='HP-V1'):\n"
        "    raise NotImplementedError('TODO_FACTORY_GENERATION')\n",
        encoding="utf-8",
    )

    real_product_repo = REPO_ROOT.parent / "client-02-quotation"
    copied_main = False
    try:
        if (real_product_repo / "main.py").is_file():
            shutil.copyfile(real_product_repo / "main.py", product_dir / "main.py")
            copied_main = True
    except OSError:
        copied_main = False
    if not copied_main:
        (product_dir / "main.py").write_text(
            "import json, sys\nfrom quotation.calculator import QuotationValidationError, calculate_quotation\n"
            "def main():\n    return 0\n",
            encoding="utf-8",
        )

    copied_test = False
    try:
        if (real_product_repo / "tests" / "test_quotation_s6.py").is_file():
            shutil.copyfile(
                real_product_repo / "tests" / "test_quotation_s6.py",
                product_dir / "tests" / "test_quotation_s6.py",
            )
            copied_test = True
    except OSError:
        copied_test = False
    if not copied_test:
        (product_dir / "tests" / "test_quotation_s6.py").write_text(
            "import pytest\n"
            "from quotation.calculator import QuotationValidationError, calculate_quotation\n\n"
            "def test_q01_q03_e01():\n"
            "    q01 = calculate_quotation([{'sku': 'HP-BOX', 'quantity': 1}])\n"
            "    assert q01['goods_net_cents'] == 250\n"
            "    assert q01['shipping_cents'] == 1200\n"
            "    assert q01['total_cents'] == 1450\n"
            "    q03 = calculate_quotation([{'sku': 'HP-BOX', 'quantity': 50}])\n"
            "    assert q03['lines'][0]['list_amount_cents'] == 12500\n"
            "    assert q03['lines'][0]['discount_cents'] == 625\n"
            "    assert q03['goods_net_cents'] == 11875\n"
            "    assert q03['shipping_cents'] == 1200\n"
            "    assert q03['total_cents'] == 13075\n"
            "    with pytest.raises(QuotationValidationError):\n"
            "        calculate_quotation([{'sku': 'HP-BOX', 'quantity': 0}])\n",
            encoding="utf-8",
        )
    return product_dir


class FakeS6ArchitectLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "architecture_decisions": [
                        "Implement deterministic HP-V1 Python calculation in quotation/calculator.py using integer cents and Decimal ROUND_HALF_UP.",
                        "Load unit prices from unchanged data/HansePack_Katalog.json without any Factory or LLM runtime dependency.",
                    ],
                    "ready_for_implementation": True,
                    "summary": "Planned HansePack Session 6 quotation calculation module.",
                }
            )
        )


class FakeS6ValidImplementationLLM:
    def invoke(self, messages):
        payload = {
            **HANSEPACK_S6_REQUIRED_RULES,
            "summary": "Implemented deterministic HP-V1 quotation logic with ROUND_HALF_UP and E01 validation.",
        }
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


class FakeS6IncompleteImplementationLLM:
    """Omits shipping_fee_cents and rounding_mode to confirm strict rejection without fallback."""

    def invoke(self, messages):
        incomplete = dict(HANSEPACK_S6_REQUIRED_RULES)
        incomplete.pop("shipping_fee_cents")
        incomplete.pop("rounding_mode")
        incomplete["summary"] = "Incomplete rule payload."
        return AIMessage(content=json.dumps(incomplete, ensure_ascii=False))


class FakeS6BrokenCodeImplementationLLM:
    """Supplies raw Python code that still contains placeholder / syntax defect."""

    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "python_code": "def calculate_quotation(items): TODO_FACTORY_GENERATION",
                    "summary": "Broken python code output.",
                }
            )
        )


class FakeS6QALLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "summary": "Verified Q01, Q03, E01, and fixture provenance in tests/test_quotation_s6.py.",
                    "pytest_exit_code": 0,
                    "findings": [],
                    "human_approval_required": True,
                }
            )
        )


def test_project_switch_config_loads_quotation02_and_preserves_website01() -> None:
    """A1, L6.1: Verify quotation-02 configures HansePack separately without altering website-01."""
    nw_cfg = load_project_config("website-01")
    hp_cfg = load_project_config("quotation-02")

    assert nw_cfg["project_id"] == "website-01"
    assert nw_cfg["product_repo_path"] == "../client-01-website"
    assert nw_cfg["allowed_write_prefixes"] == ["site/"]
    assert nw_cfg["target_product_file"] == "site/index.html"

    assert hp_cfg["project_id"] == "quotation-02"
    assert hp_cfg["customer_task_id"] == "HP-S6-001"
    assert hp_cfg["product_repo_path"] == "../client-02-quotation"
    assert hp_cfg["allowed_write_prefixes"] == ["quotation/"]
    assert hp_cfg["target_product_file"] == "quotation/calculator.py"
    assert hp_cfg["product_test_target"] == "tests/test_quotation_s6.py"

    hp_task, hp_rules = build_task_from_project_config("quotation-02")
    assert isinstance(hp_task, CustomerDeliveryTask)
    assert hp_task.project_id == "quotation-02"
    assert hp_task.task_id == "HP-S6-001"
    assert hp_task.allowed_write_prefixes == ["quotation/"]
    assert hp_rules["rule_version"] == "HP-V1"
    assert hp_rules["shipping_fee_cents"] == "1200"
    assert "N-01" not in hp_rules


def test_project_isolation_hansepack_run_never_modifies_nordwerk_files(
    tmp_path: Path,
) -> None:
    """A4, B5, L6.1 (Feedback Point 1): Verify HansePack workflow execution leaves the full Session 5
    Nordwerk release (84d5baf, including site/index.html and English site/en.html) untouched and separately testable.
    """
    nordwerk_dir = _create_s6_temp_nordwerk_checkout(tmp_path)
    hansepack_dir = _create_s6_temp_hansepack_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    nordwerk_before = _snapshot_tree_hashes(nordwerk_dir)
    assert "site/index.html" in nordwerk_before
    assert "site/en.html" in nordwerk_before
    assert "docs/security-advisory-sr01.md" in nordwerk_before
    assert (
        validate_rendered_html_pre_gate(
            (nordwerk_dir / "site" / "index.html").read_text(encoding="utf-8"),
            SESSION_05_CR01_REQUIRED_CONTENT,
            en_html=(nordwerk_dir / "site" / "en.html").read_text(encoding="utf-8"),
        )
        == []
    )

    # Sandbox must reject any attempt to escape HansePack repo into Nordwerk (German or English page) or modify fixtures/tests
    for escaped_nordwerk_target in (
        "../client-01-website/site/index.html",
        "../client-01-website/site/en.html",
    ):
        with pytest.raises(ValueError, match="escapes configured product workspace"):
            validate_product_workspace_path(
                hansepack_dir,
                escaped_nordwerk_target,
                for_write=True,
                allowed_write_prefixes=["quotation/"],
            )

    with pytest.raises(ValueError, match="outside allowed product directories"):
        write_product_file_tool(
            hansepack_dir,
            "data/HansePack_Katalog.json",
            "{}",
            allowed_write_prefixes=["quotation/"],
        )

    with pytest.raises(ValueError, match="outside allowed product directories"):
        write_product_file_tool(
            hansepack_dir,
            "tests/test_quotation_s6.py",
            "# tampered",
            allowed_write_prefixes=["quotation/"],
        )

    task, req_rules = build_task_from_project_config(
        "quotation-02",
        product_repo_path=str(hansepack_dir),
        workflow_id="WF-QUOTATION02-ISOLATION-TEST",
    )
    res = run_customer_delivery_workflow(
        task,
        project_id="quotation-02",
        required_content=req_rules,
        architect_llm=FakeS6ArchitectLLM(),
        implementation_llm=FakeS6ValidImplementationLLM(),
        qa_llm=FakeS6QALLM(),
        runs_root=runs_dir,
    )

    assert res.project_id == "quotation-02"
    assert res.final_qa_result is not None
    assert res.final_qa_result.status == "passed"
    assert res.human_gate_status == "pending_approval"

    nordwerk_after = _snapshot_tree_hashes(nordwerk_dir)
    assert nordwerk_after == nordwerk_before

    # Confirm the untouched Nordwerk S5 release (84d5baf, including site/en.html) still passes its own product tests
    nw_exit_code, _ = run_product_test_tool(
        nordwerk_dir,
        "tests/test_website_s5.py",
    )
    assert nw_exit_code == 0


def test_hansepack_s6_workflow_delivers_q01_q03_e01_and_records_review(
    tmp_path: Path,
) -> None:
    """A2, A3, B1..B4, L6.2: Verify multi-agent handover, Q01/Q03/E01 checks, manifest, and human review."""
    hansepack_dir = _create_s6_temp_hansepack_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    task, req_rules = build_task_from_project_config(
        "quotation-02",
        product_repo_path=str(hansepack_dir),
        workflow_id="WF-QUOTATION02-UNIT-01",
    )
    res = run_customer_delivery_workflow(
        task,
        project_id="quotation-02",
        required_content=req_rules,
        architect_llm=FakeS6ArchitectLLM(),
        implementation_llm=FakeS6ValidImplementationLLM(),
        qa_llm=FakeS6QALLM(),
        runs_root=runs_dir,
    )

    assert res.iterations_used == 1
    assert isinstance(res.architect_result.handover, ProductHandoverPayload)
    assert res.architect_result.handover.to_role == "backend_api_engineer"

    imp_step = res.implementation_history[-1]
    assert imp_step.status == "completed"
    assert imp_step.written_file == "quotation/calculator.py"
    assert imp_step.handover.pre_gate_validation_passed is True
    assert isinstance(imp_step.handover, QAHandoverPayload)
    assert imp_step.handover.to_role == "qa_test_engineer"

    assert res.final_qa_result is not None
    assert res.final_qa_result.status == "passed"
    assert res.final_qa_result.pytest_exit_code == 0
    assert res.human_gate_status == "pending_approval"

    manifest = json.loads(Path(res.manifest_file).read_text(encoding="utf-8"))
    assert manifest["project_id"] == "quotation-02"
    assert manifest["customer_task_id"] == "HP-S6-001"
    assert manifest["product_test_passed"] is True
    assert "quotation/calculator.py" in manifest["artifact_hashes"]
    assert any("client-02-quotation" in ref for ref in manifest["issue_and_pr_references"])

    report_path = Path(res.run_directory) / "workflow-report.json"
    rev_path = record_customer_human_review(
        report_path,
        reviewer="saad",
        decision="approved",
        tested_source_commit="11223344556677889900aabbccddeeff00112233",
        rationale="Verified Q01, Q03, and E01 rejection against unchanged customer fixtures.",
    )
    rev_data = json.loads(rev_path.read_text(encoding="utf-8"))
    assert rev_data["decision"] == "approved"
    assert rev_data["project_id"] == "quotation-02"
    assert "quotation/calculator.py" in rev_data["reviewed_artifact_hashes"]


def test_hansepack_missing_or_invalid_llm_fields_rejected_without_fallback(
    tmp_path: Path,
) -> None:
    """A4: Verify incomplete LLM output or invalid Python code fails pre-gate and escalates to human."""
    hansepack_dir = _create_s6_temp_hansepack_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    # Case 1: Missing required rules in LLM JSON output
    bad_task = CustomerDeliveryTask(
        task_id="HP-S6-MISSING-RULES",
        workflow_id="WF-QUOTATION02-MISSING",
        project_id="quotation-02",
        product_repo_path=str(hansepack_dir),
        input_files=["docs/issue-01-session-06.md", "quotation/calculator.py"],
        target_product_file="quotation/calculator.py",
        product_test_target="tests/test_quotation_s6.py",
        allowed_write_prefixes=["quotation/"],
        max_correction_loops=2,
    )
    res_bad = run_customer_delivery_workflow(
        bad_task,
        project_id="quotation-02",
        required_content=dict(HANSEPACK_S6_REQUIRED_RULES),
        architect_llm=FakeS6ArchitectLLM(),
        implementation_llm=FakeS6IncompleteImplementationLLM(),
        qa_llm=FakeS6QALLM(),
        runs_root=runs_dir,
    )
    assert res_bad.iterations_used == 2
    assert all(step.status == "error" for step in res_bad.implementation_history)
    assert all(step.written_file is None for step in res_bad.implementation_history)
    assert res_bad.human_gate_status == "escalate_to_human"
    assert "TODO_FACTORY_GENERATION" in (
        hansepack_dir / "quotation" / "calculator.py"
    ).read_text(encoding="utf-8")

    # Case 2: Broken python_code fails pre-gate syntax/placeholder check
    broken_task = CustomerDeliveryTask(
        task_id="HP-S6-BROKEN-CODE",
        workflow_id="WF-QUOTATION02-BROKEN",
        project_id="quotation-02",
        product_repo_path=str(hansepack_dir),
        input_files=["docs/issue-01-session-06.md", "quotation/calculator.py"],
        target_product_file="quotation/calculator.py",
        product_test_target="tests/test_quotation_s6.py",
        allowed_write_prefixes=["quotation/"],
        max_correction_loops=1,
    )
    res_broken = run_customer_delivery_workflow(
        broken_task,
        project_id="quotation-02",
        required_content=dict(HANSEPACK_S6_REQUIRED_RULES),
        architect_llm=FakeS6ArchitectLLM(),
        implementation_llm=FakeS6BrokenCodeImplementationLLM(),
        qa_llm=FakeS6QALLM(),
        runs_root=runs_dir,
    )
    assert res_broken.implementation_history[-1].status == "error"
    assert "Pre-gate Python quotation validation failed" in res_broken.implementation_history[-1].summary
    assert res_broken.human_gate_status == "escalate_to_human"


def test_session_06_feedback_ci_credits_person_hours_and_github_issues() -> None:
    """Session 6 Feedback Point 1 & Point 2:
    1. Verify 3 GitHub Actions CI runs on 2026-11-16 are recorded with 3.0 credits in costs/usage.csv & cost-model.yaml.
    2. Verify human person-hours (Personenstunden) on 2026-11-16 are itemized per individual team member and exclusive category.
    3. Verify real GitHub Issue URLs (client-02-quotation/issues/1 & agentic_ai_haw_2627/issues/4) are linked in config and run manifests.
    4. Verify frozen Nordwerk commit in cost-model.yaml references the Session 5 release 84d5baf (including site/en.html).
    """
    import yaml

    usage_csv = REPO_ROOT / "costs" / "usage.csv"
    with usage_csv.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.reader(handle))
    for idx, r in enumerate(raw_rows[1:], start=2):
        assert len(r) == 8, f"Row {idx} in costs/usage.csv has {len(r)} columns: {r}"

    with usage_csv.open(newline="", encoding="utf-8-sig") as handle:
        dict_rows = list(csv.DictReader(handle))

    s6_rows = [r for r in dict_rows if r["date"] == "2026-11-16"]
    s6_ci_rows = [r for r in s6_rows if r["actor_type"] == "ci"]
    assert len(s6_ci_rows) == 1
    assert float(s6_ci_rows[0]["quantity"]) == 3.0
    assert float(s6_ci_rows[0]["credits"]) == 3.0

    s6_human_rows = [r for r in s6_rows if r["actor_type"] == "human"]
    assert len(s6_human_rows) == 11
    valid_members = {"yaw", "saad", "felix", "minh", "mirko", "muhammad"}
    for h_row in s6_human_rows:
        assert "+" not in h_row["actor"], f"Human row must specify single actor, got {h_row['actor']}"
        assert h_row["actor"] in valid_members
        assert h_row["notes"].startswith("Category: ")
        assert abs(float(h_row["quantity"]) * 100.0 - float(h_row["credits"])) < 1e-6

    total_s6_human_hours = sum(float(r["quantity"]) for r in s6_human_rows)
    total_s6_human_credits = sum(float(r["credits"]) for r in s6_human_rows)
    assert abs(total_s6_human_hours - 2.50) < 1e-6
    assert abs(total_s6_human_credits - 250.0) < 1e-6

    cost_model = yaml.safe_load((REPO_ROOT / "costs" / "cost-model.yaml").read_text(encoding="utf-8"))
    assert cost_model["ci"]["runs"] == 13
    s6_calc = cost_model["credits_calculation"]["session_06_breakdown"]
    assert float(s6_calc["session_06_ci_credits"]) == 3.0
    assert "84d5baf9fcfebd9b1c4772e63fcd6b92d70fc53f" in s6_calc["nordwerk_frozen_commit"]
    assert "53885e0" not in s6_calc["nordwerk_frozen_commit"]
    assert "https://github.com/minhnyn/client-02-quotation/issues/1" in s6_calc["github_issue_urls"]

    hp_cfg = load_project_config("quotation-02")
    assert "https://github.com/minhnyn/client-02-quotation/issues/1" in hp_cfg["github_issue_urls"]
    assert "https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/4" in hp_cfg["github_issue_urls"]

    for wf_id in ("WF-QUOTATION02-S6-001", "WF-QUOTATION02-S6-002"):
        m_path = REPO_ROOT / "runs" / "quotation-02" / wf_id / "manifest.json"
        m_data = json.loads(m_path.read_text(encoding="utf-8"))
        assert "https://github.com/minhnyn/client-02-quotation/issues/1" in m_data["issue_and_pr_references"]
        assert "https://github.com/mfadhilahm/agentic_ai_haw_2627/issues/4" in m_data["issue_and_pr_references"]


class _FlakyS6ImplementationLLM:
    """Fails on iteration 1 (missing max_quantity), succeeds on iteration 2."""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            bad = dict(HANSEPACK_S6_REQUIRED_RULES)
            bad.pop("max_quantity")
            bad["summary"] = "Iteration 1 missing max_quantity."
            return AIMessage(content=json.dumps(bad, ensure_ascii=False))
        return FakeS6ValidImplementationLLM().invoke(messages)


class _SpyS6QALLM:
    """Tracks exact number of QA LLM invocations to verify pre-QA short-circuit."""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return FakeS6QALLM().invoke(messages)


def test_generic_python_contract_and_pre_qa_short_circuit_on_failed_implementation(
    tmp_path: Path,
) -> None:
    """Session 6 Feedback Point 3:
    1. Verify generic Python contract validator & AST pre-gate validate non-HansePack Python contracts as well
       as declarative project templates from config/projects/templates/.
    2. Verify failed implementation steps are intercepted before an unnecessary QA run (0 QA LLM calls and
       0.0 QA credits on failed implementation iterations).
    """
    # 1. Generic non-HansePack contract validation & AST pre-gate check
    custom_required = {
        "service_version": "SVC-V1",
        "max_batch_size": "50",
        "mode": "STRICT",
    }
    custom_contract = {
        "required_classes": ["CustomServiceError"],
        "required_functions": ["compute_custom_metric"],
        "integer_rule_keys": {"max_batch_size": 1},
        "enum_rule_keys": {"mode": ["STRICT", "LENIENT"]},
        "rule_constant_map": {
            "service_version": "SERVICE_VERSION",
            "max_batch_size": "MAX_BATCH_SIZE",
            "mode": "MODE",
        },
    }
    normalized_custom = validate_and_normalize_python_contract_fields(
        {"service_version": "SVC-V1", "max_batch_size": "50", "mode": "STRICT"},
        required_content=custom_required,
        contract=custom_contract,
    )
    assert normalized_custom == {
        "service_version": "SVC-V1",
        "max_batch_size": 50,
        "mode": "STRICT",
    }

    custom_py = (
        'SERVICE_VERSION = "SVC-V1"\n'
        "MAX_BATCH_SIZE = 50\n"
        'MODE = "STRICT"\n'
        "class CustomServiceError(ValueError):\n"
        "    pass\n"
        "def compute_custom_metric(x: int) -> int:\n"
        "    return x * MAX_BATCH_SIZE\n"
    )
    assert (
        validate_python_module_pre_gate(
            custom_py,
            required_content=custom_required,
            contract=custom_contract,
        )
        == []
    )

    # Verify external template rendering from config/projects/quotation-02.yaml
    hp_cfg = load_project_config("quotation-02")
    rendered_hp = render_python_module_from_contract(
        HANSEPACK_S6_REQUIRED_RULES,
        required_content=HANSEPACK_S6_REQUIRED_RULES,
        contract=hp_cfg["python_module_contract"],
    )
    assert (
        validate_python_module_pre_gate(
            rendered_hp,
            required_content=HANSEPACK_S6_REQUIRED_RULES,
            contract=hp_cfg["python_module_contract"],
        )
        == []
    )

    # 2. Verify Pre-QA Short-Circuit: Iteration 1 fails implementation -> 0 QA LLM calls on Iteration 1;
    # Iteration 2 succeeds -> 1 QA LLM call total across the 2-iteration workflow.
    hansepack_dir = _create_s6_temp_hansepack_checkout(tmp_path)
    runs_dir = tmp_path / "runs"
    flaky_imp_llm = _FlakyS6ImplementationLLM()
    spy_qa_llm = _SpyS6QALLM()

    task, req_rules = build_task_from_project_config(
        "quotation-02",
        product_repo_path=str(hansepack_dir),
        workflow_id="WF-QUOTATION02-SHORT-CIRCUIT",
    )
    res = run_customer_delivery_workflow(
        task,
        project_id="quotation-02",
        required_content=req_rules,
        architect_llm=FakeS6ArchitectLLM(),
        implementation_llm=flaky_imp_llm,
        qa_llm=spy_qa_llm,
        runs_root=runs_dir,
    )
    assert res.iterations_used == 2
    assert flaky_imp_llm.calls == 2
    assert spy_qa_llm.calls == 1
    assert res.qa_history[0].status == "failed"
    assert res.qa_history[0].tool_status == "not_started"
    assert "Pre-QA short-circuit" in res.qa_history[0].summary
    assert res.qa_history[1].status == "passed"
    assert res.qa_history[1].tool_status == "completed"
    assert res.human_gate_status == "pending_approval"

    # When implementation fails on all iterations, QA LLM is called 0 times (0.0 QA credits)
    spy_qa_all_fail = _SpyS6QALLM()
    fail_task, _ = build_task_from_project_config(
        "quotation-02",
        product_repo_path=str(hansepack_dir),
        workflow_id="WF-QUOTATION02-ALL-FAIL-SHORT-CIRCUIT",
    )
    res_all_fail = run_customer_delivery_workflow(
        fail_task,
        project_id="quotation-02",
        required_content=req_rules,
        architect_llm=FakeS6ArchitectLLM(),
        implementation_llm=FakeS6IncompleteImplementationLLM(),
        qa_llm=spy_qa_all_fail,
        runs_root=runs_dir,
    )
    assert res_all_fail.iterations_used == 2
    assert spy_qa_all_fail.calls == 0
    assert all(q.tool_status == "not_started" for q in res_all_fail.qa_history)
