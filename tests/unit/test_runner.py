"""
Tests for agents.runner: starting a workflow, pausing for approval, and
resuming after an approve/reject decision.

These exercise the real compiled graphs (not mocked node functions),
mocking only the two external boundaries: the LLM call in generate_plan
and the MCP tool call in execute_step. Skipped entirely if `langgraph`
isn't installed.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

pytest.importorskip("langgraph", reason="langgraph not installed in this environment")

from agents import runner  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_workflow_store():
    """Each test starts from a clean in-memory workflow store."""
    runner._workflow_store.clear()
    yield
    runner._workflow_store.clear()


class TestStartWorkflow:
    @pytest.mark.asyncio
    async def test_low_risk_plan_runs_to_success(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {"query": "report"}}]
        with (
            patch("agents.graph.generate_plan", return_value=plan),
            patch("agents.graph.execute_step", return_value={"count": 1, "files": [{"id": "f1"}]}),
        ):
            workflow_id, state = await runner.start_workflow("find the report", role="analyst")

        assert state["status"] == "SUCCEEDED"
        assert runner.get_workflow(workflow_id) is state

    @pytest.mark.asyncio
    async def test_high_risk_step_pauses_for_approval(self):
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "x@example.com"}}]
        with patch("agents.graph.generate_plan", return_value=plan):
            workflow_id, state = await runner.start_workflow("email the customer", role="manager")

        assert state["status"] == "AWAITING_APPROVAL"
        assert runner.get_workflow(workflow_id)["status"] == "AWAITING_APPROVAL"

    @pytest.mark.asyncio
    async def test_policy_denied_step_fails_immediately(self):
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "x@example.com"}}]
        with patch("agents.graph.generate_plan", return_value=plan):
            _, state = await runner.start_workflow("email the customer", role="analyst")

        assert state["status"] == "FAILED"


class TestApproveStep:
    @pytest.mark.asyncio
    async def test_approving_resumes_and_completes_the_step(self):
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "x@example.com"}}]
        with patch("agents.graph.generate_plan", return_value=plan):
            workflow_id, paused_state = await runner.start_workflow("email the customer", role="manager")
        assert paused_state["status"] == "AWAITING_APPROVAL"

        with patch(
            "agents.graph.execute_step", return_value={"message_id": "m1", "thread_id": "t1"}
        ):
            final_state = await runner.approve_step(workflow_id, approve=True)

        assert final_state["status"] == "SUCCEEDED"
        assert final_state["results"][0] == {"message_id": "m1", "thread_id": "t1"}

    @pytest.mark.asyncio
    async def test_rejecting_fails_without_executing(self):
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {"to": "x@example.com"}}]
        with patch("agents.graph.generate_plan", return_value=plan):
            workflow_id, _ = await runner.start_workflow("email the customer", role="manager")

        with patch("agents.graph.execute_step") as mock_execute:
            final_state = await runner.approve_step(workflow_id, approve=False)
            mock_execute.assert_not_called()

        assert final_state["status"] == "FAILED"
        assert "rejected" in final_state["final_result"]["error"]

    @pytest.mark.asyncio
    async def test_unknown_workflow_id_raises(self):
        with pytest.raises(runner.WorkflowNotFoundError):
            await runner.approve_step("not-a-real-id", approve=True)

    @pytest.mark.asyncio
    async def test_approving_a_non_paused_workflow_raises(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {"query": "x"}}]
        with (
            patch("agents.graph.generate_plan", return_value=plan),
            patch("agents.graph.execute_step", return_value={"count": 0, "files": []}),
        ):
            workflow_id, state = await runner.start_workflow("find x", role="analyst")
        assert state["status"] == "SUCCEEDED"

        with pytest.raises(runner.WorkflowNotAwaitingApprovalError):
            await runner.approve_step(workflow_id, approve=True)


class TestGetWorkflow:
    def test_returns_none_for_unknown_id(self):
        assert runner.get_workflow("does-not-exist") is None
