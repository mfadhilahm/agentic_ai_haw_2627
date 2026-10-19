import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from src.agents.dev_architect_agent import (
    REPO_ROOT,
    DevArchitectRequest,
    load_role_metadata,
    read_repo_file_tool,
    run_dev_architect_agent,
    write_repo_file_tool,
)


class FakeDevArchitectLLM:
    def invoke(self, messages):
        prompt_text = "\n".join(getattr(m, "content", "") for m in messages)
        if "software_architect" in prompt_text or "Software Architect" in prompt_text:
            return AIMessage(
                content=json.dumps(
                    {
                        "status": "completed",
                        "summary": "High-level architecture specification and interface contract.",
                        "decisions_or_contracts": [
                            "Define modular service layer and persistence contract.",
                            "Expose RESTful endpoints following existing FastAPI conventions.",
                        ],
                        "proposed_changes": [
                            {
                                "file_path": "docs/adr-001.md",
                                "action": "create",
                                "description": "Architecture decision record.",
                                "code_snippet": "",
                            }
                        ],
                        "human_approval_required": True,
                    }
                )
            )
        return AIMessage(
            content=json.dumps(
                {
                    "status": "completed",
                    "summary": "Backend service implementation plan.",
                    "decisions_or_contracts": [
                        "Follow repository database connection and route patterns."
                    ],
                    "proposed_changes": [
                        {
                            "file_path": "src/app/service.py",
                            "action": "create",
                            "description": "Service module implementation.",
                            "code_snippet": "def execute_service() -> dict: ...",
                        }
                    ],
                    "human_approval_required": True,
                }
            )
        )


def test_role_metadata_loaded_dynamically_from_roles_yaml() -> None:
    sa_meta = load_role_metadata("software_architect")
    assert sa_meta.role_id == "software_architect"
    assert sa_meta.agent_id == "dev_architect_agent"
    assert sa_meta.accountable_human == "minh"

    bae_meta = load_role_metadata("backend_api_engineer")
    assert bae_meta.role_id == "backend_api_engineer"
    assert bae_meta.agent_id == "dev_architect_agent"
    assert bae_meta.accountable_human == "mirko"


def test_read_tool_rejects_outside_repo_and_protected_files() -> None:
    with pytest.raises(ValueError, match="escapes repository root"):
        read_repo_file_tool("../outside.txt")

    with pytest.raises(ValueError, match="protected path"):
        read_repo_file_tool(".env")

    with pytest.raises(ValueError, match="protected path"):
        read_repo_file_tool(".git/config")


def test_write_tool_blocks_secrets_and_starter_boundary() -> None:
    with pytest.raises(ValueError, match="escapes repository root"):
        write_repo_file_tool("../outside.txt", "data")

    with pytest.raises(ValueError, match="protected path"):
        write_repo_file_tool(".env", "SECRET=1")

    with pytest.raises(ValueError, match="protected path"):
        write_repo_file_tool(".env.local", "SECRET=1")

    with pytest.raises(ValueError, match="starter boundary"):
        write_repo_file_tool("examples/hack.py", "print('no')")

    with pytest.raises(ValueError, match="starter boundary"):
        write_repo_file_tool("tests/starter/test_hack.py", "def test_x(): pass")


def test_architect_and_backend_roles_are_distinguishable_and_traced(tmp_path: Path) -> None:
    trace_file = tmp_path / "dev-arch-trace.jsonl"
    artifact_rel = "evidence/session-02/test-sa-artifact.md"
    artifact_abs = REPO_ROOT / artifact_rel

    try:
        # 1. Run as Software Architect
        sa_result = run_dev_architect_agent(
            DevArchitectRequest(
                task_id="TEST-SA-001",
                description="Design component boundaries and API contract.",
                assigned_role="software_architect",
                input_files=["src/app/main.py", "src/app/db.py"],
                output_artifact_path=artifact_rel,
            ),
            llm=FakeDevArchitectLLM(),
            trace_file=str(trace_file),
        )

        assert sa_result.status == "completed"
        assert sa_result.role == "software_architect"
        assert sa_result.agent == "dev_architect_agent"
        assert sa_result.written_artifact_path == artifact_rel
        assert artifact_abs.is_file()

        # 2. Run as Backend API Engineer
        bae_result = run_dev_architect_agent(
            DevArchitectRequest(
                task_id="TEST-BAE-001",
                description="Implement backend endpoints and service logic.",
                assigned_role="backend_api_engineer",
                input_files=["src/app/main.py", "src/app/db.py"],
            ),
            llm=FakeDevArchitectLLM(),
            trace_file=str(trace_file),
        )

        assert bae_result.status == "completed"
        assert bae_result.role == "backend_api_engineer"
        assert bae_result.agent == "dev_architect_agent"
        assert bae_result.proposed_changes[0].file_path == "src/app/service.py"

        traces = [
            json.loads(line)
            for line in trace_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(traces) == 2
        assert traces[0]["agent"] == "dev_architect_agent"
        assert traces[0]["role"] == "software_architect"
        assert traces[0]["accountable_human"] == "minh"
        assert "write_repo_file_tool" in traces[0]["tools"]

        assert traces[1]["agent"] == "dev_architect_agent"
        assert traces[1]["role"] == "backend_api_engineer"
        assert traces[1]["accountable_human"] == "mirko"
        assert "read_repo_file_tool" in traces[1]["tools"]
    finally:
        if artifact_abs.exists():
            artifact_abs.unlink()


def test_dev_architect_agent_handles_missing_file_error(tmp_path: Path) -> None:
    trace_file = tmp_path / "error-trace.jsonl"
    result = run_dev_architect_agent(
        DevArchitectRequest(
            task_id="TEST-ERR-001",
            description="Attempt to inspect a non-existent file.",
            assigned_role="backend_api_engineer",
            input_files=["src/app/does_not_exist.py"],
        ),
        llm=FakeDevArchitectLLM(),
        trace_file=str(trace_file),
    )

    assert result.status == "error"
    assert "FileNotFoundError" in result.summary
    trace = json.loads(trace_file.read_text(encoding="utf-8").splitlines()[0])
    assert trace["status"] == "error"
