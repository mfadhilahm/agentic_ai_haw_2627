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

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_delivery_workflow import (
    HANSEPACK_S6_REQUIRED_RULES,
    build_task_from_project_config,
    load_project_config,
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


def _snapshot_tree_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def _create_s6_temp_nordwerk_checkout(tmp_path: Path) -> Path:
    """Create an isolated temporary Nordwerk checkout to test project isolation."""
    nordwerk_dir = tmp_path / "client-01-website"
    (nordwerk_dir / "site").mkdir(parents=True, exist_ok=True)
    (nordwerk_dir / "tests").mkdir(parents=True, exist_ok=True)
    (nordwerk_dir / "site" / "index.html").write_text(
        "<!DOCTYPE html><html lang='de'><body><h1>Nordwerk Industrie-Service</h1></body></html>\n",
        encoding="utf-8",
    )
    (nordwerk_dir / "site" / "styles.css").write_text(
        "body { margin: 0; }\n",
        encoding="utf-8",
    )
    (nordwerk_dir / "tests" / "test_website_s5.py").write_text(
        "def test_ok():\n    assert True\n",
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
    if (real_product_repo / "main.py").is_file():
        shutil.copyfile(real_product_repo / "main.py", product_dir / "main.py")
    else:
        (product_dir / "main.py").write_text(
            "import json, sys\nfrom quotation.calculator import QuotationValidationError, calculate_quotation\n"
            "def main():\n    return 0\n",
            encoding="utf-8",
        )

    if (real_product_repo / "tests" / "test_quotation_s6.py").is_file():
        shutil.copyfile(
            real_product_repo / "tests" / "test_quotation_s6.py",
            product_dir / "tests" / "test_quotation_s6.py",
        )
    else:
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
    """A4, L6.1: Verify HansePack workflow execution leaves all Nordwerk files untouched and enforces sandbox."""
    nordwerk_dir = _create_s6_temp_nordwerk_checkout(tmp_path)
    hansepack_dir = _create_s6_temp_hansepack_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    nordwerk_before = _snapshot_tree_hashes(nordwerk_dir)

    # Sandbox must reject any attempt to escape HansePack repo into Nordwerk or modify fixtures/tests
    with pytest.raises(ValueError, match="escapes configured product workspace"):
        validate_product_workspace_path(
            hansepack_dir,
            "../client-01-website/site/index.html",
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
