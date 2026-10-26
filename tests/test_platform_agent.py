import json

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from src.agents.platform_agent import (
    PlatformAgentResult,
    PlatformTask,
    inspect_agent_architecture_tool,
    record_platform_human_review,
    run_platform_agent,
    run_platform_to_qa_workflow,
)
from src.agents.quality_agent import run_quality_agent
from src.models.tasks import EngineeringTask


class FakePlatformLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "role_executed": "agent_engineer",
                    "summary": "Platform agent verified LangGraph architecture and contracts.",
                    "findings": [],
                    "human_gate_status": "pending_approval",
                    "human_approval_required": True,
                }
            )
        )


class SelfApprovingPlatformLLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "role_executed": "agent_engineer",
                    "summary": "LLM attempting to bypass human gate.",
                    "findings": [],
                    "human_gate_status": "approved",
                    "human_approval_required": False,
                }
            )
        )


class FakeQALLM:
    def invoke(self, messages):
        return AIMessage(
            content=json.dumps(
                {
                    "status": "passed",
                    "summary": "QA agent verified the handed-over pytest target.",
                    "pytest_exit_code": 0,
                    "findings": [],
                    "human_approval_required": True,
                }
            )
        )


def test_platform_tool_rejects_paths_outside_src_and_tests() -> None:
    try:
        inspect_agent_architecture_tool(["organization/roles.yaml"])
    except ValueError:
        pass
    else:
        raise AssertionError("Path outside src/ and tests/ should be rejected")


def test_platform_agent_distinguishes_agent_and_integration_roles(tmp_path) -> None:
    trace_file = tmp_path / "platform-trace.jsonl"

    res_agent = run_platform_agent(
        PlatformTask(
            task_id="TEST-PLAT-AE-01",
            workflow_id="WF-TEST-01",
            assigned_role="agent_engineer",
            input_files=["src/agents/qa_test_agent.py"],
        ),
        llm=FakePlatformLLM(),
        trace_file=str(trace_file),
    )
    assert res_agent.status == "passed"
    assert res_agent.role_executed == "agent_engineer"
    assert res_agent.handover is not None
    assert res_agent.handover.from_role == "agent_engineer"

    res_integration = run_platform_agent(
        PlatformTask(
            task_id="TEST-PLAT-IE-01",
            workflow_id="WF-TEST-01",
            assigned_role="integration_engineer",
            input_files=["src/app/main.py", "src/agents/qa_test_agent.py"],
        ),
        llm=FakePlatformLLM(),
        trace_file=str(trace_file),
    )
    assert res_integration.status == "passed"
    assert res_integration.role_executed == "integration_engineer"
    assert res_integration.handover is not None
    assert res_integration.handover.from_role == "integration_engineer"

    lines = [
        json.loads(line)
        for line in trace_file.read_text(encoding="utf-8").splitlines()
    ]
    assert len(lines) == 2
    assert lines[0]["agent"] == "platform-agent"
    assert lines[0]["role"] == "agent_engineer"
    assert lines[0]["tools"] == ["inspect_agent_architecture_tool"]
    assert lines[1]["agent"] == "platform-agent"
    assert lines[1]["role"] == "integration_engineer"
    assert lines[1]["tools"] == ["inspect_integration_contracts_tool"]


def test_platform_agent_handles_missing_file_error(tmp_path) -> None:
    trace_file = tmp_path / "platform-error-trace.jsonl"
    result = run_platform_agent(
        PlatformTask(
            task_id="TEST-PLAT-ERR-01",
            assigned_role="agent_engineer",
            input_files=["src/agents/does_not_exist.py"],
        ),
        llm=FakePlatformLLM(),
        trace_file=str(trace_file),
    )
    assert result.status == "error"
    assert result.human_gate_status == "escalate_to_human"


def test_llm_cannot_override_human_approval_or_self_approve(tmp_path) -> None:
    trace_file = tmp_path / "platform-self-approve-trace.jsonl"
    result = run_platform_agent(
        PlatformTask(
            task_id="TEST-PLAT-GATE-01",
            assigned_role="agent_engineer",
            input_files=["src/agents/qa_test_agent.py"],
        ),
        llm=SelfApprovingPlatformLLM(),
        trace_file=str(trace_file),
    )
    assert result.status == "passed"
    assert result.human_approval_required is True
    assert result.human_gate_status == "pending_approval"

    with pytest.raises(ValidationError):
        PlatformAgentResult(
            status="passed",
            role_executed="agent_engineer",
            summary="Attempted bypass",
            human_approval_required=False,  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        PlatformAgentResult(
            status="passed",
            role_executed="agent_engineer",
            summary="Attempted self-approval",
            human_gate_status="approved",  # type: ignore[arg-type]
        )


def test_platform_to_qa_handover_workflow_and_separate_human_review(tmp_path) -> None:
    trace_file = tmp_path / "workflow-trace.jsonl"
    report_path = tmp_path / "platform-qa-report.json"
    wf_result = run_platform_to_qa_workflow(
        PlatformTask(
            task_id="TEST-WF-001",
            workflow_id="WF-HANDOVER-001",
            assigned_role="integration_engineer",
            input_files=["src/app/main.py", "src/agents/qa_test_agent.py"],
            pytest_target="tests/starter/test_api.py",
            timeout_seconds=30,
        ),
        platform_llm=FakePlatformLLM(),
        qa_llm=FakeQALLM(),
        trace_file=str(trace_file),
        report_path=str(report_path),
    )
    assert wf_result.platform_result.status == "passed"
    assert wf_result.qa_result is not None
    assert wf_result.qa_result.status == "passed"
    assert wf_result.human_approval_required is True
    assert wf_result.human_gate_status == "pending_approval"
    assert wf_result.approved_by_human is None
    assert report_path.exists()

    review_path = record_platform_human_review(
        report_path,
        reviewer="muhammad",
        decision="approved",
        notes="Reviewed integration contract and QA test execution.",
    )
    assert review_path.exists()
    review_data = json.loads(review_path.read_text(encoding="utf-8"))
    assert review_data["task_id"] == "TEST-WF-001"
    assert review_data["workflow_id"] == "WF-HANDOVER-001"
    assert review_data["decision"] == "approved"
    assert review_data["reviewer"] == "muhammad"
    assert len(review_data["report_sha256"]) == 64
    # Ensure original workflow report remains immutable in pending_approval
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_report["human_gate_status"] == "pending_approval"
    assert saved_report["approved_by_human"] is None


def test_shared_engineering_task_used_by_platform_and_quality_agents(tmp_path) -> None:
    trace_file = tmp_path / "shared-task-trace.jsonl"
    shared_task = EngineeringTask(
        task_id="SHARED-TASK-001",
        workflow_id="WF-SHARED-001",
        task_type="platform_and_qa_verification",
        description="Shared EngineeringTask from src/models/tasks.py executed across agents.",
        assigned_role="agent_engineer",
        input_files=["src/app/main.py"],
    )

    platform_res = run_platform_agent(
        shared_task, llm=FakePlatformLLM(), trace_file=str(trace_file)
    )
    assert platform_res.status == "passed"
    assert platform_res.handover is not None

    quality_task = platform_res.handover.to_quality_task(timeout_seconds=30)
    quality_res = run_quality_agent(
        quality_task, llm=FakeQALLM(), trace_file=str(trace_file)
    )
    assert quality_res.status == "awaiting_human_review"

    traces = [
        json.loads(line)
        for line in trace_file.read_text(encoding="utf-8").splitlines()
    ]
    assert len(traces) >= 2
    assert {t["workflow_id"] for t in traces} == {"WF-SHARED-001"}
    assert {t["task_id"] for t in traces} == {"SHARED-TASK-001"}


def test_platform_to_qa_workflow_error_short_circuits_and_cannot_be_approved(tmp_path) -> None:
    trace_file = tmp_path / "workflow-error-trace.jsonl"
    report_path = tmp_path / "workflow-error-report.json"
    wf_result = run_platform_to_qa_workflow(
        PlatformTask(
            task_id="TEST-WF-ERR-001",
            workflow_id="WF-HANDOVER-ERR-001",
            assigned_role="integration_engineer",
            input_files=["src/app/non_existent_endpoint.py"],
            pytest_target="tests/starter/test_api.py",
            timeout_seconds=30,
        ),
        platform_llm=FakePlatformLLM(),
        qa_llm=FakeQALLM(),
        trace_file=str(trace_file),
        report_path=str(report_path),
    )
    assert wf_result.platform_result.status == "error"
    assert wf_result.qa_result is None
    assert wf_result.human_gate_status == "escalate_to_human"
    assert wf_result.approved_by_human is None

    with pytest.raises(ValueError, match="pending_approval"):
        record_platform_human_review(
            report_path,
            reviewer="saad",
            decision="approved",
        )

    escalation_review = record_platform_human_review(
        report_path,
        reviewer="saad",
        decision="changes_requested",
        notes="Missing endpoint file must be fixed before approval.",
    )
    assert escalation_review.exists()
