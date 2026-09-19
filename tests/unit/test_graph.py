"""
Unit tests for the individual node functions and routing functions in
agents/graph.py.

These test the nodes as plain functions (mocking generate_plan and
execute_step) rather than compiling and running the full LangGraph graph,
since that requires the `langgraph` package to be importable. If
`langgraph` isn't installed, this whole module is skipped rather than
failing the rest of the suite.

Run from the repo root:
    pytest tests/unit/test_graph.py -v
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

langgraph = pytest.importorskip("langgraph", reason="langgraph not installed in this environment")

from agents import graph  # noqa: E402
from agents.state import new_workflow_state  # noqa: E402


def _state_with_plan(plan, **overrides):
    # Default role="admin" so tests that aren't specifically about policy
    # denial don't accidentally get denied by the Policy Engine. Tests
    # that DO want to exercise denial pass role="analyst" (or another
    # restricted role) explicitly via overrides.
    state = new_workflow_state("test request", role="admin")
    state["plan"] = plan
    state["status"] = "RUNNING"
    state.update(overrides)
    return state


class TestPlannerNode:
    @pytest.mark.asyncio
    async def test_successful_plan_sets_running(self):
        fake_plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {"query": "x"}}]
        with patch("agents.graph.generate_plan", return_value=fake_plan):
            update = await graph.planner_node(new_workflow_state("find the report"))

        assert update["status"] == "RUNNING"
        assert update["plan"] == fake_plan
        assert update["current_step_index"] == 0

    @pytest.mark.asyncio
    async def test_empty_plan_fails(self):
        with patch("agents.graph.generate_plan", return_value=[]):
            update = await graph.planner_node(new_workflow_state("do the impossible"))

        assert update["status"] == "FAILED"
        assert "error" in update["final_result"]


class TestRiskCheckNode:
    def test_low_risk_tool_proceeds(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan)
        update = graph.risk_check_node(state)
        assert update["status"] == "RUNNING"
        assert update["risk_levels"][0] == "LOW"

    def test_high_risk_tool_without_approval_pauses(self):
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {}}]
        state = _state_with_plan(plan)
        update = graph.risk_check_node(state)
        assert update["status"] == "AWAITING_APPROVAL"
        assert update["risk_levels"][0] == "HIGH"

    def test_high_risk_tool_with_approval_proceeds(self):
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {}}]
        state = _state_with_plan(plan, approved_steps={0})
        update = graph.risk_check_node(state)
        assert update["status"] == "RUNNING"

    def test_policy_denied_tool_fails_the_run(self):
        # analyst has no email.send permission (see policies/default_roles.py),
        # so the Policy Engine must deny this before RiskEngine is even
        # consulted — the run fails closed rather than pausing for approval.
        plan = [{"step_index": 0, "tool_name": "gmail.send", "arguments": {}}]
        state = _state_with_plan(plan, role="analyst")
        update = graph.risk_check_node(state)
        assert update["status"] == "FAILED"
        assert "error" in update["final_result"]
        assert update["errors"][0].startswith("Policy denied")

    def test_unknown_role_is_denied_by_default(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan, role="not_a_real_role")
        update = graph.risk_check_node(state)
        assert update["status"] == "FAILED"

    def test_allowed_low_risk_tool_for_restricted_role_still_proceeds(self):
        # analyst DOES have files.read, so a LOW-risk Drive tool should
        # still go through even though the role is restricted overall.
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan, role="analyst")
        update = graph.risk_check_node(state)
        assert update["status"] == "RUNNING"


class TestExecutorNode:
    @pytest.mark.asyncio
    async def test_success_records_result_and_clears_error(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan, errors={0: "stale error from a previous attempt"})

        with patch("agents.graph.execute_step", return_value={"count": 1}):
            update = await graph.executor_node(state)

        assert update["results"][0] == {"count": 1}
        assert 0 not in update["errors"]

    @pytest.mark.asyncio
    async def test_failure_records_error_not_result(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan)

        async def _raise(_step):
            raise RuntimeError("MCP server unreachable")

        with patch("agents.graph.execute_step", side_effect=_raise):
            update = await graph.executor_node(state)

        assert 0 not in update["results"]
        assert "MCP server unreachable" in update["errors"][0]


class TestVerifierNode:
    def test_passing_intermediate_step_advances_index(self):
        # drive.read has no tool-specific verification rule, so a
        # generic non-null dict result is enough to pass.
        plan = [
            {"step_index": 0, "tool_name": "drive.read", "arguments": {}},
            {"step_index": 1, "tool_name": "drive.read", "arguments": {}},
        ]
        state = _state_with_plan(plan, results={0: {"ok": True}})
        update = graph.verifier_node(state)
        assert update["current_step_index"] == 1
        assert update["status"] == "RUNNING"
        assert update["last_step_passed"] is True

    def test_passing_final_step_succeeds(self):
        plan = [{"step_index": 0, "tool_name": "drive.read", "arguments": {}}]
        state = _state_with_plan(plan, results={0: {"ok": True}})
        update = graph.verifier_node(state)
        assert update["status"] == "SUCCEEDED"
        assert update["current_step_index"] == 1

    def test_failing_step_does_not_advance(self):
        plan = [{"step_index": 0, "tool_name": "drive.read", "arguments": {}}]
        state = _state_with_plan(plan, errors={0: "boom"})
        update = graph.verifier_node(state)
        assert update["status"] == "RUNNING"
        assert update["last_step_passed"] is False
        assert "current_step_index" not in update

    def test_tool_specific_rule_failure_is_recorded_as_an_error(self):
        # drive.search DOES have a rule: its reported count must match
        # the length of the files list it returned. Here they disagree.
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan, results={0: {"count": 5, "files": [{"id": "f1"}]}})
        update = graph.verifier_node(state)
        assert update["last_step_passed"] is False
        assert 0 in update["errors"]
        assert update["verifications"][0]["passed"] is False

    def test_tool_specific_rule_success_records_verification(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan, results={0: {"count": 1, "files": [{"id": "f1"}]}})
        update = graph.verifier_node(state)
        assert update["status"] == "SUCCEEDED"
        assert update["verifications"][0]["passed"] is True


class TestRecoveryNode:
    def test_increments_attempt_count_and_retries(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan, attempt_counts={0: 0})
        update = graph.recovery_node(state)
        assert update["attempt_counts"][0] == 1
        assert update["status"] == "RUNNING"

    def test_gives_up_after_max_retries(self):
        plan = [{"step_index": 0, "tool_name": "drive.search", "arguments": {}}]
        state = _state_with_plan(plan, attempt_counts={0: graph.decide_recovery.__globals__["MAX_RETRIES"]})
        update = graph.recovery_node(state)
        assert update["status"] == "FAILED"
        assert "error" in update["final_result"]

    def test_gives_up_immediately_on_permanent_error(self):
        plan = [{"step_index": 0, "tool_name": "database.query", "arguments": {}}]
        state = _state_with_plan(
            plan, attempt_counts={0: 0}, errors={0: "Table 'ghost' does not exist in the public schema."}
        )
        update = graph.recovery_node(state)
        assert update["status"] == "FAILED"
        assert update["attempt_counts"][0] == 1


class TestRoutingFunctions:
    def test_route_after_planner_ends_on_failure(self):
        state = {"status": "FAILED"}
        assert graph.route_after_planner(state) == "end"

    def test_route_after_planner_proceeds_otherwise(self):
        state = {"status": "RUNNING"}
        assert graph.route_after_planner(state) == "risk_check"

    def test_route_after_risk_check_ends_on_awaiting_approval(self):
        state = {"status": "AWAITING_APPROVAL"}
        assert graph.route_after_risk_check(state) == "end"

    def test_route_after_risk_check_ends_on_policy_denial(self):
        state = {"status": "FAILED"}
        assert graph.route_after_risk_check(state) == "end"

    def test_route_after_risk_check_proceeds_to_executor(self):
        state = {"status": "RUNNING"}
        assert graph.route_after_risk_check(state) == "executor"

    def test_route_after_verifier_ends_on_success(self):
        state = {"status": "SUCCEEDED", "current_step_index": 1, "plan": [{}]}
        assert graph.route_after_verifier(state) == "end"

    def test_route_after_verifier_recovers_on_failure(self):
        state = {
            "status": "RUNNING",
            "current_step_index": 0,
            "plan": [{}, {}],
            "errors": {0: "boom"},
        }
        assert graph.route_after_verifier(state) == "recovery"

    def test_route_after_verifier_continues_after_pass(self):
        state = {
            "status": "RUNNING",
            "current_step_index": 1,
            "plan": [{}, {}],
            "errors": {},
        }
        assert graph.route_after_verifier(state) == "risk_check"

    def test_route_after_recovery_retries(self):
        state = {"status": "RUNNING"}
        assert graph.route_after_recovery(state) == "executor"

    def test_route_after_recovery_ends_on_give_up(self):
        state = {"status": "FAILED"}
        assert graph.route_after_recovery(state) == "end"


class TestBuildGraph:
    def test_graph_compiles_without_error(self):
        compiled = graph.build_graph()
        assert compiled is not None


class TestBuildResumeGraph:
    def test_resume_graph_compiles_without_error(self):
        compiled = graph.build_resume_graph()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_resume_graph_skips_planner_and_uses_existing_plan(self):
        # A state that's already "mid-run": plan exists, current step is
        # approved, so invoking the resume graph should execute that step
        # rather than generating a brand-new plan.
        plan = [{"step_index": 0, "tool_name": "drive.read", "arguments": {"file_id": "f1"}}]
        state = _state_with_plan(plan, role="admin", approved_steps={0})

        resume_graph = graph.build_resume_graph()
        with patch("agents.graph.execute_step", return_value={"ok": True}):
            final_state = await resume_graph.ainvoke(state)

        assert final_state["status"] == "SUCCEEDED"
        assert final_state["results"][0] == {"ok": True}
