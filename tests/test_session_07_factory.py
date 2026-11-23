"""Session 7 Factory unit tests verifying:
1. Session 7 Task Configuration & Factory Reuse (A1, A2, L7.1):
   - HP-S7-001 configures tests/test_quotation_s7.py, discount_tier_50_min_qty=50, discount_tier_100_min_qty=100,
     and delivers quotation/calculator.py with full Q01-Q14, E01-E10, and consistent JSON export helpers
     (pending_approval -> approved).
2. Controlled 5% Discount Boundary Fault Gate (A3, A4, D1, L7.2, L7.3):
   - HP-S7-FAULT-001 sets the 5% discount boundary to strictly above 50 (quantity > 50 / min_qty 51) instead of
     from 50 (quantity >= 50).
   - Unchanged customer reference tests (tests/test_quotation_s7.py) detect that Q03 yields 13700 instead of
     13075 cents, fail QA (pytest_exit_code != 0, status="failed"), and block release approval (escalate_to_human).
   - Subsequent corrected HP-S7-001 delivery restores >= 50 (Q03 = 13075 cents), passes QA, and is approved.
3. Isolated R-02 Reference Baseline Configuration & Execution (C1, C3, L7.4):
   - R-02 configures tests/verify_r02_baseline.py and calculation_note="Net amounts; shipping shown separately."
   - Executes cleanly on an isolated copy of Q-BASE without altering the customer candidate checkout.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_delivery_workflow import (
    HANSEPACK_R02_REQUIRED_RULES,
    HANSEPACK_S6_REQUIRED_RULES,
    HANSEPACK_S7_FAULT_REQUIRED_RULES,
    HANSEPACK_S7_REQUIRED_RULES,
    build_task_from_project_config,
    load_project_config,
    record_customer_human_review,
    render_python_module_from_contract,
    run_customer_delivery_workflow,
    validate_python_module_pre_gate,
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


def _create_s7_temp_hansepack_checkout(tmp_path: Path, dirname: str = "client-02-quotation") -> Path:
    """Create an isolated temporary HansePack checkout with unchanged customer fixtures and S7/R-02 tests."""
    product_dir = tmp_path / dirname
    (product_dir / "data").mkdir(parents=True, exist_ok=True)
    (product_dir / "docs").mkdir(parents=True, exist_ok=True)
    (product_dir / "quotation").mkdir(parents=True, exist_ok=True)
    (product_dir / "tests").mkdir(parents=True, exist_ok=True)

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
        "# Issue #2: [HP-S7-001] HansePack Session 7 Full HP-V1 Quotation & JSON Export\n"
        "Scope: HP-AC01..HP-AC07 (Q01-Q14, E01-E10, web UI & JSON export).\n",
        encoding="utf-8",
    )
    (product_dir / "quotation" / "__init__.py").write_text(
        "from quotation.calculator import QuotationValidationError, calculate_quotation, load_catalogue\n",
        encoding="utf-8",
    )

    # Seed with Session 6 baseline calculator (before S7 export helpers)
    s6_calc = render_python_module_from_contract(HANSEPACK_S6_REQUIRED_RULES)
    (product_dir / "quotation" / "calculator.py").write_text(s6_calc, encoding="utf-8")

    # Write independent Session 7 business test suite (verifies all Q01-Q14 under HP-V1, all E01-E10, and JSON export)
    (product_dir / "tests" / "test_quotation_s7.py").write_text(
        "import json\n"
        "from pathlib import Path\n"
        "import pytest\n"
        "from quotation.calculator import (\n"
        "    QuotationValidationError,\n"
        "    build_quotation_export_payload,\n"
        "    calculate_quotation,\n"
        "    export_quotation_json,\n"
        ")\n\n"
        "REPO_ROOT = Path(__file__).resolve().parents[1]\n"
        "REF_PATH = REPO_ROOT / 'data' / 'HansePack_Referenzfaelle.json'\n\n"
        "def _ref_data():\n"
        "    return json.loads(REF_PATH.read_text(encoding='utf-8'))\n\n"
        "def test_all_valid_cases_q01_to_q14_hp_v1():\n"
        "    data = _ref_data()\n"
        "    assert len(data['valid_cases']) == 14\n"
        "    for case in data['valid_cases']:\n"
        "        cid = case['id']\n"
        "        res = calculate_quotation(case['input']['items'])\n"
        "        exp_v1 = case['expected']['HP-V1']\n"
        "        assert res['currency'] == exp_v1['currency'], f'{cid} currency'\n"
        "        assert res['rule_version'] == exp_v1['rule_version'], f'{cid} rule_version'\n"
        "        if res['total_cents'] != exp_v1['total_cents']:\n"
        "            pytest.fail(\n"
        "                f\"{cid} total_cents mismatch: got {res['total_cents']}, expected {exp_v1['total_cents']} \"\n"
        "                f\"(goods_net_cents={res['goods_net_cents']} vs {exp_v1['goods_net_cents']})\",\n"
        "                pytrace=False,\n"
        "            )\n"
        "        assert res['goods_net_cents'] == exp_v1['goods_net_cents'], f'{cid} goods_net_cents'\n"
        "        assert res['shipping_cents'] == exp_v1['shipping_cents'], f'{cid} shipping_cents'\n"
        "        assert len(res['lines']) == len(case['expected_lines']), f'{cid} line count'\n"
        "        for got_line, exp_line in zip(res['lines'], case['expected_lines']):\n"
        "            for k in ('sku', 'quantity', 'unit_price_cents', 'list_amount_cents', 'discount_percent', 'discount_cents', 'net_cents'):\n"
        "                assert got_line[k] == exp_line[k], f'{cid} line {k}: got {got_line[k]}, expected {exp_line[k]}'\n\n"
        "def test_all_invalid_cases_e01_to_e10_rejected():\n"
        "    data = _ref_data()\n"
        "    assert len(data['invalid_cases']) == 10\n"
        "    for case in data['invalid_cases']:\n"
        "        with pytest.raises(QuotationValidationError) as ctx:\n"
        "            calculate_quotation(case['input']['items'])\n"
        "        assert ctx.value.reason == case['expected_reason'], case['id']\n\n"
        "def test_consistent_json_export_q12():\n"
        "    items = [{'sku': 'HP-BOX', 'quantity': 50}, {'sku': 'HP-TAPE', 'quantity': 10}]\n"
        "    calc = calculate_quotation(items)\n"
        "    exported = json.loads(export_quotation_json(items))\n"
        "    assert exported == build_quotation_export_payload(calc)\n"
        "    assert exported['goods_net_cents'] == 15875\n"
        "    assert exported['shipping_cents'] == 1200\n"
        "    assert exported['total_cents'] == 17075\n",
        encoding="utf-8",
    )

    # Write R-02 baseline verification test (verifies calculation_note + all Q01-Q14 and E01-E10)
    (product_dir / "tests" / "verify_r02_baseline.py").write_text(
        "import json\n"
        "from quotation.calculator import calculate_quotation, export_quotation_json\n"
        "from tests.test_quotation_s7 import (\n"
        "    test_all_invalid_cases_e01_to_e10_rejected,\n"
        "    test_all_valid_cases_q01_to_q14_hp_v1,\n"
        ")\n\n"
        "def test_r02_calculation_note_and_all_s7_business_tests():\n"
        "    test_all_valid_cases_q01_to_q14_hp_v1()\n"
        "    test_all_invalid_cases_e01_to_e10_rejected()\n"
        "    q03 = calculate_quotation([{'sku': 'HP-BOX', 'quantity': 50}])\n"
        "    assert q03.get('calculation_note') == 'Net amounts; shipping shown separately.'\n"
        "    exported = json.loads(export_quotation_json([{'sku': 'HP-BOX', 'quantity': 50}]))\n"
        "    assert exported.get('calculation_note') == 'Net amounts; shipping shown separately.'\n"
        "    assert exported['goods_net_cents'] == 11875\n"
        "    assert exported['shipping_cents'] == 1200\n"
        "    assert exported['total_cents'] == 13075\n",
        encoding="utf-8",
    )
    return product_dir


class FakeS7ArchitectLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "architecture_decisions": [
                        "Implement full HP-V1 quotation calculator (Q01-Q14, E01-E10) with ROUND_HALF_UP and integer cents.",
                        "Provide build_quotation_export_payload and export_quotation_json so UI display and JSON download share identical calculated data.",
                    ],
                    "ready_for_implementation": True,
                    "summary": "Planned Session 7 HansePack quotation and JSON export delivery.",
                }
            )
        )


class FakeS7ValidImplementationLLM:
    """Emits valid HP-S7-001 rules (discount_tier_50_min_qty=50, discount_tier_100_min_qty=100)."""

    def invoke(self, messages):
        payload = {
            **HANSEPACK_S7_REQUIRED_RULES,
            "summary": "Implemented full HP-V1 quotation logic (5% discount >= 50) and JSON export helpers.",
        }
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


class FakeS7DiscountBoundaryFaultImplementationLLM:
    """Emits the controlled Session 7 business fault: 5% discount starts at > 50 (min_qty=51) instead of >= 50."""

    def invoke(self, messages):
        payload = {
            **HANSEPACK_S7_FAULT_REQUIRED_RULES,
            "summary": "Injected controlled discount boundary fault: 5% discount only above 50 (from 51).",
        }
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


class FakeR02ImplementationLLM:
    """Emits the isolated R-02 baseline rule payload including calculation_note."""

    def invoke(self, messages):
        payload = {
            **HANSEPACK_R02_REQUIRED_RULES,
            "summary": "Added calculation_note to exported quotation JSON for R-02 baseline.",
        }
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


class FakeS7QALLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "summary": "Executed Session 7 HansePack product test suite.",
                    "pytest_exit_code": 0,
                    "findings": [],
                    "human_approval_required": True,
                }
            )
        )


def test_s7_task_configurations_in_quotation02_yaml() -> None:
    """A1, C1: Verify HP-S7-001, HP-S7-FAULT-001, and R-02 load cleanly from config/projects/quotation-02.yaml."""
    cfg = load_project_config("quotation-02")
    assert "s7_customer_task" in cfg
    assert "s7_fault_task" in cfg
    assert "r02_reference_task" in cfg

    # 1. HP-S7-001
    s7_task, s7_rules = build_task_from_project_config("quotation-02", task_id="HP-S7-001")
    assert isinstance(s7_task, CustomerDeliveryTask)
    assert s7_task.task_id == "HP-S7-001"
    assert s7_task.product_test_target == "tests/test_quotation_s7.py"
    assert s7_task.target_product_file == "quotation/calculator.py"
    assert s7_task.allowed_write_prefixes == ["quotation/"]
    assert s7_rules["rule_version"] == "HP-V1"
    assert s7_rules["discount_tier_50_min_qty"] == "50"
    assert s7_rules["discount_tier_100_min_qty"] == "100"
    assert "calculation_note" not in s7_rules

    # 2. HP-S7-FAULT-001 (controlled discount boundary fault: > 50 / min_qty 51)
    fault_task, fault_rules = build_task_from_project_config(
        "quotation-02", task_id="HP-S7-FAULT-001"
    )
    assert fault_task.task_id == "HP-S7-FAULT-001"
    assert fault_task.product_test_target == "tests/test_quotation_s7.py"
    assert fault_task.max_correction_loops == 1
    assert fault_rules["discount_tier_50_min_qty"] == "51"
    assert fault_rules["discount_tier_100_min_qty"] == "100"

    # 3. R-02 (isolated reference baseline task)
    r02_task, r02_rules = build_task_from_project_config("quotation-02", task_id="R-02")
    assert r02_task.task_id == "R-02"
    assert r02_task.product_test_target == "tests/verify_r02_baseline.py"
    assert r02_rules["discount_tier_50_min_qty"] == "50"
    assert r02_rules["calculation_note"] == "Net amounts; shipping shown separately."


def test_s7_customer_delivery_passes_and_controlled_discount_fault_blocks_gate(
    tmp_path: Path,
) -> None:
    """A2, A3, A4, D1, L7.1, L7.2, L7.3:
    1. Controlled fault HP-S7-FAULT-001 sets 5% discount boundary to > 50 (min_qty 51), causing Q03 to
       produce 13700 instead of 13075 cents; tests/test_quotation_s7.py fails QA and blocks gate approval
       (human_gate_status == 'escalate_to_human').
    2. Corrected run HP-S7-001 restores >= 50 (min_qty 50), passes all Q01-Q14, E01-E10, and JSON export checks,
       reaches 'pending_approval', and is approved by a named human reviewer.
    """
    hansepack_dir = _create_s7_temp_hansepack_checkout(tmp_path)
    runs_dir = tmp_path / "runs"

    # Step 1: Controlled Fault Run (HP-S7-FAULT-001: 5% discount only above 50 -> Q03 yields 13700 != 13075)
    fault_task, fault_rules = build_task_from_project_config(
        "quotation-02",
        product_repo_path=str(hansepack_dir),
        task_id="HP-S7-FAULT-001",
        workflow_id="WF-QUOTATION02-S7-FAULT-001",
    )
    res_fault = run_customer_delivery_workflow(
        fault_task,
        project_id="quotation-02",
        required_content=fault_rules,
        architect_llm=FakeS7ArchitectLLM(),
        implementation_llm=FakeS7DiscountBoundaryFaultImplementationLLM(),
        qa_llm=FakeS7QALLM(),
        runs_root=runs_dir,
    )

    # Implementation wrote the faulty module (DISCOUNT_TIER_50_MIN_QTY = 51), which passes syntax/AST pre-gate
    # but MUST fail the independent business test suite (Q03: 13700 != 13075) in product_qa_node!
    assert res_fault.implementation_history[-1].status == "completed"
    assert res_fault.implementation_history[-1].written_file == "quotation/calculator.py"
    fault_code = (hansepack_dir / "quotation" / "calculator.py").read_text(encoding="utf-8")
    assert "DISCOUNT_TIER_50_MIN_QTY = 51" in fault_code

    assert res_fault.final_qa_result is not None
    assert res_fault.final_qa_result.status == "failed"
    assert res_fault.final_qa_result.pytest_exit_code != 0
    assert any("13700" in f.description and "13075" in f.description for f in res_fault.final_qa_result.findings)
    assert res_fault.human_gate_status == "escalate_to_human"

    fault_manifest = json.loads(Path(res_fault.manifest_file).read_text(encoding="utf-8"))
    assert fault_manifest["product_test_passed"] is False

    # Gate MUST prevent human approval of the faulty run
    fault_report_path = Path(res_fault.run_directory) / "workflow-report.json"
    with pytest.raises(ValueError, match="pending_approval"):
        record_customer_human_review(
            fault_report_path,
            reviewer="felix",
            decision="approved",
            rationale="Must not approve when Q03 business test failed with 13700 vs 13075 cents.",
        )

    # Reviewer records explicit rejection (changes_requested) on the blocked fault run
    fault_rev_path = record_customer_human_review(
        fault_report_path,
        reviewer="felix",
        decision="changes_requested",
        rationale="Controlled 5% discount boundary fault (> 50 / min_qty 51) failed Q03 (13700 vs 13075 cents); blocked at quality gate.",
    )
    fault_rev = json.loads(fault_rev_path.read_text(encoding="utf-8"))
    assert fault_rev["decision"] == "changes_requested"
    assert "uncommitted_worktree (rejected_not_committed)" in fault_rev["product_worktree_state"]

    # Step 2: Corrected Session 7 Customer Delivery Run (HP-S7-001: 5% discount >= 50 -> Q03 = 13075 cents)
    s7_task, s7_rules = build_task_from_project_config(
        "quotation-02",
        product_repo_path=str(hansepack_dir),
        task_id="HP-S7-001",
        workflow_id="WF-QUOTATION02-S7-001",
    )
    res_ok = run_customer_delivery_workflow(
        s7_task,
        project_id="quotation-02",
        required_content=s7_rules,
        architect_llm=FakeS7ArchitectLLM(),
        implementation_llm=FakeS7ValidImplementationLLM(),
        qa_llm=FakeS7QALLM(),
        runs_root=runs_dir,
    )

    assert res_ok.iterations_used == 1
    assert isinstance(res_ok.architect_result.handover, ProductHandoverPayload)
    assert res_ok.architect_result.handover.to_role == "backend_api_engineer"

    imp_ok = res_ok.implementation_history[-1]
    assert imp_ok.status == "completed"
    assert imp_ok.written_file == "quotation/calculator.py"
    assert imp_ok.handover.pre_gate_validation_passed is True
    assert isinstance(imp_ok.handover, QAHandoverPayload)
    assert imp_ok.handover.to_role == "qa_test_engineer"

    fixed_code = (hansepack_dir / "quotation" / "calculator.py").read_text(encoding="utf-8")
    assert "DISCOUNT_TIER_50_MIN_QTY = 50" in fixed_code
    assert "def export_quotation_json(" in fixed_code

    assert res_ok.final_qa_result is not None
    assert res_ok.final_qa_result.status == "passed"
    assert res_ok.final_qa_result.pytest_exit_code == 0
    assert res_ok.human_gate_status == "pending_approval"

    ok_manifest = json.loads(Path(res_ok.manifest_file).read_text(encoding="utf-8"))
    assert ok_manifest["customer_task_id"] == "HP-S7-001"
    assert ok_manifest["product_test_passed"] is True

    ok_report_path = Path(res_ok.run_directory) / "workflow-report.json"
    ok_rev_path = record_customer_human_review(
        ok_report_path,
        reviewer="saad",
        decision="approved",
        tested_source_commit="aa11bb22cc33dd44ee55ff6677889900aabbccdd",
        rationale="Verified Q01-Q14, E01-E10, JSON export consistency, and Q03 recovery (13075 cents).",
    )
    ok_rev = json.loads(ok_rev_path.read_text(encoding="utf-8"))
    assert ok_rev["decision"] == "approved"
    assert ok_rev["subsequent_product_commit"] == "aa11bb22cc33dd44ee55ff6677889900aabbccdd"


def test_r02_baseline_executes_on_isolated_qbase_copy_without_touching_customer_candidate(
    tmp_path: Path,
) -> None:
    """C1, C3, L7.4: Verify R-02 adds calculation_note='Net amounts; shipping shown separately.' on an isolated
    copy of Q-BASE while leaving the customer candidate checkout completely untouched.
    """
    qbase_candidate_dir = _create_s7_temp_hansepack_checkout(
        tmp_path, dirname="client-02-quotation-qbase"
    )
    # Render clean S7 Q-BASE candidate state into qbase_candidate_dir
    qbase_calc = render_python_module_from_contract(
        HANSEPACK_S7_REQUIRED_RULES,
        required_content=HANSEPACK_S7_REQUIRED_RULES,
    )
    (qbase_candidate_dir / "quotation" / "calculator.py").write_text(
        qbase_calc, encoding="utf-8"
    )
    qbase_before = _snapshot_tree_hashes(qbase_candidate_dir)

    # Create an isolated copy of Q-BASE for the R-02 baseline experiment
    r02_isolated_dir = tmp_path / "client-02-quotation-r02-experiment"
    shutil.copytree(qbase_candidate_dir, r02_isolated_dir)
    runs_dir = tmp_path / "runs"

    r02_task, r02_rules = build_task_from_project_config(
        "quotation-02",
        product_repo_path=str(r02_isolated_dir),
        task_id="R-02",
        workflow_id="R-02-BASELINE-UNIT-001",
    )
    res_r02 = run_customer_delivery_workflow(
        r02_task,
        project_id="quotation-02",
        required_content=r02_rules,
        architect_llm=FakeS7ArchitectLLM(),
        implementation_llm=FakeR02ImplementationLLM(),
        qa_llm=FakeS7QALLM(),
        runs_root=runs_dir,
    )

    assert res_r02.task_id == "R-02"
    assert res_r02.iterations_used == 1
    assert res_r02.implementation_history[-1].status == "completed"
    assert res_r02.final_qa_result is not None
    assert res_r02.final_qa_result.status == "passed"
    assert res_r02.final_qa_result.pytest_exit_code == 0
    assert res_r02.human_gate_status == "pending_approval"

    r02_code = (r02_isolated_dir / "quotation" / "calculator.py").read_text(
        encoding="utf-8"
    )
    assert 'CALCULATION_NOTE = "Net amounts; shipping shown separately."' in r02_code
    assert (
        validate_python_module_pre_gate(
            r02_code,
            required_content=r02_rules,
        )
        == []
    )

    # Confirm the customer Q-BASE candidate directory was never modified by the R-02 experiment
    qbase_after = _snapshot_tree_hashes(qbase_candidate_dir)
    assert qbase_after == qbase_before
    assert "Net amounts; shipping shown separately." not in (
        qbase_candidate_dir / "quotation" / "calculator.py"
    ).read_text(encoding="utf-8")
