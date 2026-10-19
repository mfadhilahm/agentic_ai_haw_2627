"""Team-owned Session 2 tests for the two ops-agent capabilities."""

import hashlib
import json

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from src.agents.ops_agent import (
    OpsRequest,
    analyze_cost_traces_tool,
    inspect_devops_tool,
    record_human_review,
    run_ops_agent,
)
from src.agents.task_models import EngineeringTask


class FakeLLM:
    def invoke(self, messages):
        return AIMessage(content=json.dumps({
            "summary": "Static audit completed; deployment remains subject to human review.",
            "recommendations": ["Review CI execution evidence before deploy."],
        }), usage_metadata={"input_tokens": 100, "output_tokens": 40})


def task(mode: str, task_id: str = "OPS-TEST-01", input_files: list[str] | None = None) -> EngineeringTask:
    return EngineeringTask(task_id=task_id, task_type="operations_audit", description="Check operations evidence",
                           assigned_role="devops_engineer" if mode == "devops" else "cost_observability_engineer",
                           workflow_id="TEST-WORKFLOW-01", input_files=input_files or [])


def test_structured_devops_audit_and_trace(tmp_path):
    trace_file = tmp_path / "trace.jsonl"
    report_dir = tmp_path / "reports"
    result = run_ops_agent(OpsRequest(task=task("devops"), mode="devops"),
                           llm=FakeLLM(), trace_file=str(trace_file), report_dir=report_dir)
    assert result.capability == "devops"
    assert result.role_id == "devops_engineer"
    assert result.devops is not None
    assert result.observability is None
    assert any(c.code == "ci_pytest" and c.status == "pass" for c in result.devops.checks)
    assert result.human_approval_required is True
    assert result.approval_decision == "pending"
    assert result.llm_status == "completed"
    assert (report_dir / f"{result.run_id}.json").is_file()
    trace = json.loads(trace_file.read_text(encoding="utf-8").splitlines()[0])
    assert trace["role"] == "devops_engineer"
    assert trace["workflow_id"] == "TEST-WORKFLOW-01"
    assert trace["task_id"] == result.task_id
    assert trace["calls"] == 1
    assert trace["input_tokens"] == 100
    assert trace["output_tokens"] == 40
    assert "inspect_devops_tool" in trace["tools"]


def test_real_trace_reading_and_course_credit_calculation(tmp_path):
    result = run_ops_agent(
        OpsRequest(task=task("observability", "OPS-COST-TEST"), mode="observability", observed_task_id="SESSION-01-QA"),
        no_llm=True, trace_file=str(tmp_path / "trace.jsonl"), report_dir=tmp_path / "reports",
    )
    audit = result.observability
    assert audit is not None
    assert audit.agent_runs == 3
    assert audit.llm_calls == 3  # explicit legacy assumption; trace lacks calls
    assert audit.runs_missing_token_counts == 1
    assert audit.input_tokens is None  # unknown is NOT measured zero
    assert audit.output_tokens is None
    assert audit.recorded_input_tokens == 252
    assert audit.recorded_output_tokens == 4760
    assert audit.agent_credits == pytest.approx(16.4369)
    assert audit.total_credits == pytest.approx(16.4369)
    assert result.llm_status == "not_requested"
    assert result.capability == "observability"
    assert result.role_id == "cost_observability_engineer"
    assert result.approval_decision == "pending"
    assert result.devops is None


def test_trace_duplicates_are_not_double_counted(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "evidence").mkdir()
    record = {"task_id": "TASK-1", "run_id": "run-1", "agent": "qa-test-agent", "duration_seconds": 10,
              "calls": 2, "input_tokens": 1000, "output_tokens": 2000, "status": "passed"}
    content = json.dumps(record) + "\n"
    (tmp_path / "logs" / "copy.jsonl").write_text(content, encoding="utf-8")
    (tmp_path / "evidence" / "copy.jsonl").write_text(content, encoding="utf-8")
    audit, _ = analyze_cost_traces_tool(tmp_path, [], "TASK-1", None)
    assert audit.agent_runs == 1
    assert audit.llm_calls == 2
    assert audit.duplicate_records == 1
    assert audit.agent_credits == pytest.approx(2.2)


def test_missing_task_traces_escalate_and_budget_flag(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "a.jsonl").write_text('', encoding='utf-8')
    audit, findings = analyze_cost_traces_tool(tmp_path, [], "NO-SUCH-TASK", 0)
    assert audit.agent_runs == 0
    assert any(f.code == "no_task_traces" for f in findings)


def test_costs_include_human_review_and_ci_without_double_counting(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "costs").mkdir()
    (tmp_path / "logs" / "trace.jsonl").write_text(json.dumps({
        "task_id": "TASK-A", "run_id": "a", "agent": "qa-agent", "calls": 1,
        "duration_seconds": 10, "input_tokens": 0, "output_tokens": 0}) + "\n", encoding="utf-8")
    (tmp_path / "costs" / "usage.csv").write_text(
        "date,task_id,actor_type,actor,quantity,unit,credits,notes\n"
        "2026-10-19,TASK-A,human,Mirko,0.5,hours,50.0,Review QA result\n"
        "2026-10-19,TASK-A,ci,GitHub Actions,1,runs,1.0,CI run\n"
        "2026-10-19,TASK-A,agent,qa-agent,1,runs,1.1,duplicated in trace\n", encoding="utf-8")
    audit, findings = analyze_cost_traces_tool(tmp_path, [], "TASK-A", 50)
    assert audit.agent_credits == pytest.approx(1.1)
    assert audit.human_review_hours == 0.5
    assert audit.human_credits == 50
    assert audit.ci_credits == 1
    assert audit.total_credits == pytest.approx(52.1)
    assert any(f.code == "budget_exceeded" for f in findings)


def test_devops_disallows_unsafe_file_inputs(tmp_path):
    with pytest.raises(ValueError):
        inspect_devops_tool(tmp_path, ["../../.env"], False, 5)
    with pytest.raises(ValueError):
        inspect_devops_tool(tmp_path, ["src/app/settings.py"], False, 5)


def test_observability_blocks_trace_paths_outside_scope(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "secret.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        analyze_cost_traces_tool(tmp_path, ["secret.jsonl"], "TASK-1", None)
    with pytest.raises(ValueError):
        analyze_cost_traces_tool(tmp_path, ["../secret.jsonl"], "TASK-1", None)


def test_invalid_inputs_and_role_mismatch_rejected():
    with pytest.raises(ValidationError):
        OpsRequest(task=task("devops"), mode="observability")
    with pytest.raises(ValidationError):
        EngineeringTask(task_id="../../oops", task_type="ops", description="x", assigned_role="devops_engineer")


def test_tool_error_returns_escalation_and_terminates(tmp_path):
    result = run_ops_agent(
        OpsRequest(task=task("observability", input_files=["logs/missing.jsonl"]), mode="observability"),
        no_llm=True, trace_file=str(tmp_path / "trace.jsonl"), report_dir=tmp_path / "reports")
    assert result.status == "error"
    assert result.approval_decision == "escalate_to_human"
    assert result.llm_status == "not_requested"
    assert any(f.code == "tool_error" for f in result.findings)
    assert len((tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_invalid_llm_response_falls_back_without_fake_approval(tmp_path):
    class BadLLM:
        def invoke(self, messages):
            return AIMessage(content="NOT JSON")
    result = run_ops_agent(OpsRequest(task=task("devops"), mode="devops"),
                           llm=BadLLM(), trace_file=str(tmp_path / "trace.jsonl"), report_dir=tmp_path / "reports")
    assert result.status == "needs_review"
    assert result.llm_status == "failed"
    assert result.approval_decision == "pending"


def test_explicit_human_decision_is_separate_and_immutable(tmp_path):
    result = run_ops_agent(OpsRequest(task=task("devops"), mode="devops"),
                           no_llm=True, trace_file=str(tmp_path / "trace.jsonl"), report_dir=tmp_path / "reports")
    report = tmp_path / "reports" / f"{result.run_id}.json"
    original = report.read_bytes()
    review_file = record_human_review(report, reviewer="Mirko", decision="changes_requested", notes="Verify actual CI logs")
    review = json.loads(review_file.read_text(encoding="utf-8"))
    assert review["task_id"] == result.task_id
    assert review["run_id"] == result.run_id
    assert review["decision"] == "changes_requested"
    assert review["reviewer"] == "Mirko"
    assert review["report_sha256"] == hashlib.sha256(original).hexdigest()
    assert report.read_bytes() == original
    with pytest.raises(FileExistsError):
        record_human_review(report, reviewer="Mirko", decision="approved")


def test_qa_handoff_accepts_shared_task_model(monkeypatch):
    from src.agents import task_handoffs
    observed = {}

    def fake_run(request, **kwargs):
        observed["task_id"] = request.task_id
        return "QA completed"

    monkeypatch.setattr(task_handoffs, "run_qa_agent", fake_run)
    shared_task = EngineeringTask(task_id="TASK-QA-1", task_type="test", description="QA acceptance tests",
                                  assigned_role="qa_test_engineer", workflow_id="WF-1")
    assert task_handoffs.run_qa_engineering_task(shared_task, pytest_target="tests/test_ops_agent.py") == "QA completed"
    assert observed["task_id"] == "TASK-QA-1"


def test_failed_audit_cannot_be_human_approved(tmp_path):
    result = run_ops_agent(OpsRequest(task=task("observability", input_files=["logs/missing.jsonl"]), mode="observability"),
                           no_llm=True, trace_file=str(tmp_path / "trace.jsonl"), report_dir=tmp_path / "reports")
    with pytest.raises(ValueError):
        record_human_review(tmp_path / "reports" / f"{result.run_id}.json", reviewer="Mirko", decision="approved")
