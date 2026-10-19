import json

from langchain_core.messages import AIMessage

from src.agents.platform_agent import (
    EngineeringTask,
    inspect_agent_architecture_tool,
    run_platform_agent,
    run_platform_to_qa_workflow,
)


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
        EngineeringTask(
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
        EngineeringTask(
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
        EngineeringTask(
            task_id="TEST-PLAT-ERR-01",
            assigned_role="agent_engineer",
            input_files=["src/agents/does_not_exist.py"],
        ),
        llm=FakePlatformLLM(),
        trace_file=str(trace_file),
    )
    assert result.status == "error"
    assert result.human_gate_status == "escalate_to_human"


def test_platform_to_qa_handover_workflow(tmp_path) -> None:
    trace_file = tmp_path / "workflow-trace.jsonl"
    wf_result = run_platform_to_qa_workflow(
        EngineeringTask(
            task_id="TEST-WF-001",
            workflow_id="WF-HANDOVER-001",
            assigned_role="integration_engineer",
            input_files=["src/app/main.py", "src/agents/qa_test_agent.py"],
            pytest_target="tests/starter/test_api.py",
        ),
        platform_llm=FakePlatformLLM(),
        qa_llm=FakeQALLM(),
        human_decision="approved",
        approved_by_human="muhammad",
        trace_file=str(trace_file),
    )
    assert wf_result.platform_result.status == "passed"
    assert wf_result.qa_result is not None
    assert wf_result.qa_result.status == "passed"
    assert wf_result.human_gate_status == "approved"
    assert wf_result.approved_by_human == "muhammad"


def test_shared_engineering_task_used_by_both_agents(tmp_path) -> None:
    from src.agents.qa_test_agent import run_qa_agent
    from src.agents.task_models import EngineeringTask as SharedEngineeringTask

    trace_file = tmp_path / "shared-task-trace.jsonl"
    shared_task = SharedEngineeringTask(
        task_id="SHARED-TASK-001",
        workflow_id="WF-SHARED-001",
        task_type="platform_and_qa_verification",
        description="Shared EngineeringTask executed by both platform-agent and qa-test-agent.",
        assigned_role="agent_engineer",
        input_files=["src/agents/qa_test_agent.py"],
        pytest_target="tests/starter/test_api.py",
        timeout_seconds=30,
    )

    platform_res = run_platform_agent(
        shared_task, llm=FakePlatformLLM(), trace_file=str(trace_file)
    )
    qa_res = run_qa_agent(
        shared_task, llm=FakeQALLM(), trace_file=str(trace_file)
    )

    assert platform_res.status == "passed"
    assert qa_res.status == "passed"

    traces = [
        json.loads(line)
        for line in trace_file.read_text(encoding="utf-8").splitlines()
    ]
    assert len(traces) == 2
    assert traces[0]["task_id"] == "SHARED-TASK-001"
    assert traces[0]["workflow_id"] == "WF-SHARED-001"
    assert traces[0]["agent"] == "platform-agent"
    assert traces[1]["task_id"] == "SHARED-TASK-001"
    assert traces[1]["workflow_id"] == "WF-SHARED-001"
    assert traces[1]["agent"] == "qa-test-agent"

