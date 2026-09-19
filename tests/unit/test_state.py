"""Unit tests for agents.state.new_workflow_state."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.state import new_workflow_state  # noqa: E402


class TestNewWorkflowState:
    def test_sets_user_request(self):
        state = new_workflow_state("find overdue invoices")
        assert state["user_request"] == "find overdue invoices"

    def test_starts_pending_with_empty_plan(self):
        state = new_workflow_state("anything")
        assert state["status"] == "PENDING"
        assert state["plan"] == []
        assert state["current_step_index"] == 0

    def test_starts_with_empty_tracking_collections(self):
        state = new_workflow_state("anything")
        assert state["results"] == {}
        assert state["errors"] == {}
        assert state["attempt_counts"] == {}
        assert state["approved_steps"] == set()

    def test_defaults_role_to_least_privileged_builtin_role(self):
        # Fail-closed default: callers who forget to pass the real
        # authenticated user's role get denied by the Policy Engine
        # rather than silently getting elevated access.
        state = new_workflow_state("anything")
        assert state["role"] == "analyst"

    def test_role_can_be_overridden(self):
        state = new_workflow_state("anything", role="admin")
        assert state["role"] == "admin"
